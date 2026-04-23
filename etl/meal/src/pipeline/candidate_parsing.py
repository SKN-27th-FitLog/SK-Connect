import os
import json
from typing import Dict, Any
from .base_stage import BaseStage
from ..core.file_manager import logger
from ..services.parsers.store_parser import StoreParser
from ..db.models.store_models import StoreCandidate
from ..core.storage.hive_path_builder import HivePathBuilder

class CandidateParsing(BaseStage):
    """
    Stage 2: Candidate Parsing
    Raw 파일을 읽어 구조화된 Candidate 데이터를 추출하고 JSONL로 저장합니다.
    """
    
    def __init__(self, parser=None, path_builder=None):
        super().__init__("Candidate Parsing")
        self.parser = parser or StoreParser()
        self.path_builder = path_builder or HivePathBuilder()

    def _execute(self, raw_file_path: str) -> Dict[str, Any]:
        """
        단일 Raw 파일을 읽어 파싱을 수행합니다.
        """
        logger.info(f"--- [Stage 2] Parsing raw file: {raw_file_path}")
        
        # 1. 파일 읽기
        try:
            with open(raw_file_path, "r", encoding="utf-8") as f:
                raw_content = f.read()
        except Exception as e:
            logger.error(f"!!! [Stage 2] Failed to read raw file: {e}")
            return {"status": "fail", "reason_code": "FILE_READ_ERROR"}

        # 2. 파싱 수행
        # TODO: 실제 운영시는 파일 메타데이터에서 원본 URL을 가져와야 함
        parse_res = self.parser.parse(raw_content, url=raw_file_path)
        
        if parse_res["status"] == "fail":
            return parse_res

        # 3. 모델 검증 (Pydantic 규약 준수)
        try:
            candidate = StoreCandidate(**parse_res)
        except Exception as e:
            logger.error(f"!!! [Stage 2] Model validation failed: {e}")
            return {"status": "fail", "reason_code": "INVALID_CANDIDATE_MODEL", "reason_detail": str(e)}

        # 4. 서비스(테이블)별 분리 저장
        platform = parse_res["source_platform"]
        internal_id = parse_res["source_internal_id"]
        
        # shop: 순수 매장 정보만 저장 (메뉴/리뷰/이미지 제외)
        self._save_candidate_file(candidate, service="shop")
        
        # menu: 메뉴 데이터 분리 저장
        menus = parse_res.get("menus", [])
        if menus:
            self._save_service_file("menu", platform, internal_id, menus)
        
        # review: 리뷰 데이터 분리 저장
        reviews = parse_res.get("reviews", [])
        if reviews:
            self._save_service_file("review", platform, internal_id, reviews)
        
        # image: 이미지 URL 분리 저장
        images = parse_res.get("images", [])
        if images:
            self._save_service_file("image", platform, internal_id, images)
        
        return {
            "status": "success",
            "candidate": candidate.model_dump(),
            "source_raw_path": raw_file_path,
            "counts": {
                "menus": len(menus),
                "reviews": len(reviews),
                "images": len(images)
            }
        }

    def _save_candidate_file(self, candidate: StoreCandidate, service: str = "shop"):
        """
        Shop Candidate를 서비스별 경로에 JSONL 형태로 저장합니다.
        """
        try:
            dir_path = self.path_builder.build(stage="candidate", status="success", service=service)
            
            if not os.path.exists(dir_path):
                os.makedirs(dir_path, exist_ok=True)
            
            file_name = f"cand_{candidate.source_platform}_{candidate.source_internal_id}.jsonl"
            full_path = f"{dir_path}/{file_name}"
            
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(candidate.model_dump_json() + "\n")
                
            logger.info(f"--- [Stage 2] Candidate saved: {full_path}")
            
        except Exception as e:
            logger.error(f"!!! [Stage 2] Failed to save candidate file: {e}")

    def _save_service_file(self, service: str, platform: str, internal_id: str, data_list: list):
        """
        메뉴/리뷰/이미지 등 서비스별 데이터를 개별 JSONL로 저장합니다.
        """
        try:
            dir_path = self.path_builder.build(stage="candidate", status="success", service=service)
            
            if not os.path.exists(dir_path):
                os.makedirs(dir_path, exist_ok=True)
            
            file_name = f"cand_{platform}_{internal_id}.jsonl"
            full_path = f"{dir_path}/{file_name}"
            
            with open(full_path, "w", encoding="utf-8") as f:
                for item in data_list:
                    f.write(json.dumps(item, ensure_ascii=False) + "\n")
                    
            logger.info(f"--- [Stage 2] {service.upper()} data saved ({len(data_list)}건): {full_path}")
            
        except Exception as e:
            logger.error(f"!!! [Stage 2] Failed to save {service} file: {e}")

