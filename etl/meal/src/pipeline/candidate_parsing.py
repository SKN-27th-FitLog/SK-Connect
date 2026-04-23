import os
import json
from typing import Dict, Any
from .base_stage import BaseStage
from ..core.file_manager import logger
from ..parsers.store_parser import StoreParser
from ..models.store_models import StoreCandidate
from ..storage.hive_path_builder import HivePathBuilder

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

        # 4. JSONL 저장
        self._save_candidate_file(candidate)
        
        return {
            "status": "success",
            "candidate": candidate.model_dump(),
            "source_raw_path": raw_file_path
        }

    def _save_candidate_file(self, candidate: StoreCandidate):
        """
        결과를 Candidate 경로에 JSONL 형태로 저장합니다.
        """
        try:
            dir_path = self.path_builder.build(stage="candidate", status="success")
            
            if not os.path.exists(dir_path):
                os.makedirs(dir_path, exist_ok=True)
            
            # 실무적 효율: store별 독립 파일로 저장 (병렬 처리 용이)
            file_name = f"cand_{candidate.source_platform}_{candidate.source_internal_id}.jsonl"
            full_path = f"{dir_path}/{file_name}"
            
            with open(full_path, "w", encoding="utf-8") as f:
                # JSONL 형식을 위해 한 줄에 기록
                f.write(candidate.model_dump_json() + "\n")
                
            logger.info(f"--- [Stage 2] Candidate saved: {full_path}")
            
        except Exception as e:
            logger.error(f"!!! [Stage 2] Failed to save candidate file: {e}")
