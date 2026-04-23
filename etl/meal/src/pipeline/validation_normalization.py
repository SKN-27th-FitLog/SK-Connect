import os
import json
from typing import Dict, Any, Optional
from .base_stage import BaseStage
from ..core.file_manager import logger
from ..services.validators.normalization import normalize_name, normalize_address
from ..db.models.store_models import NormalizedStore, StoreCandidate
from ..pipeline.dedup_service import DedupService
from ..core.storage.hive_path_builder import HivePathBuilder

class ValidationNormalization(BaseStage):
    """
    Stage 3: Validation & Normalization
    추출된 후보 데이터를 정제하고 중복 여부를 판정합니다.
    """
    
    def __init__(self, dedup_service: DedupService, path_builder: HivePathBuilder = None):
        super().__init__("Validation & Normalization")
        self.dedup_service = dedup_service
        self.path_builder = path_builder or HivePathBuilder()

    def _execute(self, candidate_file_path: str) -> Dict[str, Any]:
        """
        단일 Candidate 파일을 처리합니다.
        """
        logger.info(f"--- [Stage 3] Processing candidate: {candidate_file_path}")
        
        # 1. Candidate 데이터 로드
        try:
            with open(candidate_file_path, "r", encoding="utf-8") as f:
                line = f.readline()
                if not line: return {"status": "fail", "reason": "EMPTY_FILE"}
                data = json.loads(line)
                candidate = StoreCandidate(**data)
        except Exception as e:
            logger.error(f"!!! [Stage 3] Failed to load candidate: {e}")
            return {"status": "fail", "reason_code": "CANDIDATE_LOAD_ERROR"}

        # 2. 정규화 (Normalization)
        n_name = normalize_name(candidate.name)
        n_addr = normalize_address(candidate.address or "")
        
        # 3. 중복 체크 (Deduplication)
        # normalize된 정보를 포함하여 중복 체크 요청
        temp_data = candidate.model_dump()
        temp_data.update({"normalized_name": n_name, "normalized_address": n_addr})
        
        dedup_res = self.dedup_service.get_dedup_info(temp_data)
        
        if dedup_res["is_duplicate"]:
            logger.info(f"--- [Stage 3] Duplicate detected: {dedup_res['value']} (Type: {dedup_res['type']})")
            return {
                "status": "duplicate",
                "reason_code": "DUPLICATED_SUCCESS_STORE",
                "dedup_info": dedup_res
            }

        # 4. Normalized 모델 생성
        candidate_data = candidate.model_dump()
        # rating이 이미 들어있으므로 명시적 할당과 충돌하지 않도록 제거 후 생성
        candidate_data.pop("rating", None) 
        
        normalized = NormalizedStore(
            **candidate_data,
            normalized_name=n_name,
            normalized_address=n_addr,
            rating=candidate.rating or 0.0,
            dedup_key=dedup_res["value"] or f"{n_name}|{n_addr}",
            dedup_rule_version=dedup_res["rule_version"],
            entity_completeness=1.0
        )

        # 5. 결과 저장
        self._save_normalized_file(normalized)
        
        # 6. 부가 서비스(menu, review, image) candidate 파일을 normalized로 연계
        self._forward_auxiliary_services(candidate.source_platform, candidate.source_internal_id)
        
        return {
            "status": "success",
            "normalized_data": normalized.model_dump()
        }

    def _save_normalized_file(self, normalized: NormalizedStore):
        """
        정규화된 결과를 데이터 레이크에 저장합니다.
        """
        try:
            dir_path = self.path_builder.build(stage="normalized", status="success")
            
            if not os.path.exists(dir_path):
                os.makedirs(dir_path, exist_ok=True)
            
            file_name = f"norm_{normalized.source_platform}_{normalized.source_internal_id}.jsonl"
            full_path = f"{dir_path}/{file_name}"
            
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(normalized.model_dump_json() + "\n")
                
            logger.info(f"--- [Stage 3] Normalized data saved: {full_path}")
            
        except Exception as e:
            logger.error(f"!!! [Stage 3] Failed to save normalized file: {e}")

    def _forward_auxiliary_services(self, platform: str, internal_id: str):
        """
        메뉴, 리뷰, 이미지 파일이 있으면 그대로 normalized 스테이지로 전달합니다.
        추후 각 서비스별 별도 정규화 로직이 필요하면 분리할 수 있습니다.
        """
        import shutil
        services = ["menu", "review", "image"]
        cand_filename = f"cand_{platform}_{internal_id}.jsonl"
        norm_filename = f"norm_{platform}_{internal_id}.jsonl"
        
        for svc in services:
            cand_dir = self.path_builder.build(stage="candidate", status="success", service=svc)
            cand_path = os.path.join(cand_dir, cand_filename)
            
            if os.path.exists(cand_path):
                norm_dir = self.path_builder.build(stage="normalized", status="success", service=svc)
                os.makedirs(norm_dir, exist_ok=True)
                norm_path = os.path.join(norm_dir, norm_filename)
                
                try:
                    shutil.copy2(cand_path, norm_path)
                    logger.info(f"--- [Stage 3] {svc.upper()} data forwarded: {norm_path}")
                except Exception as e:
                    logger.error(f"!!! [Stage 3] Failed to forward {svc} file: {e}")
