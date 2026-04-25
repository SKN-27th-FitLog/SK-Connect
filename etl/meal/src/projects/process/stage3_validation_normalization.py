import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from src.core.base_stage import BaseStage
from src.core.repository.code_table_repository import CodeTableRepository, code_repo
from src.core.storage.path_builder import HivePathBuilder
from src.core.storage.jsonl_writer import JsonlWriter
from src.core.models.models import StoreModel

class Stage3ValidationNormalization(BaseStage):
    """
    [요구사항 2.2, 7.2, 10 일치] - Validation & Normalization Stage.
    데이터 정규화, 주소 코드 분리, Dedup Key 생성 수행.
    """
    NAME = "validation_normalization"

    def __init__(self, code_repository: CodeTableRepository = code_repo):
        super().__init__(self.NAME)
        self.code_repo = code_repository

    def _normalize_address(self, full_address: str, entity_id: Optional[str] = None) -> tuple[str, str]:
        if entity_id and entity_id.startswith("LA") and len(entity_id) >= 4:
            info = self.code_repo.get_address_info(entity_id)
            if info:
                detail = full_address.replace(info['name'], "").strip()
                return entity_id, detail
        
        best_match_cd = "UNKNOWN"
        detail = full_address
        addresses = self.code_repo.get_all_addresses()
        sorted_addresses = sorted(addresses.items(), key=lambda x: len(x[0]), reverse=True)
        for addr_key, info in sorted_addresses:
            if full_address.replace(" ", "").startswith(addr_key.replace(" ", "")):
                best_match_cd = info['address_cd']
                detail = full_address.replace(addr_key, "").strip()
                break
                
        return best_match_cd, detail

    def _generate_dedup_key(self, shop_data: Dict[str, Any], canonical_url: Optional[str]) -> tuple[str, str]:
        if canonical_url:
            return canonical_url, "canonical_url"
            
        name = shop_data.get("name", "").replace(" ", "")
        address = shop_data.get("full_address", "").replace(" ", "")
        if name and address:
            key_val = f"{name}|{address}"
            return key_val, "name_address"
            
        platform = shop_data.get("source_platform", "")
        pid = shop_data.get("source_internal_id", "")
        return f"{platform}|{pid}", "platform_id"

    def execute(self, candidates: List[Dict[str, Any]], batch_id: str, category_cd: str, run_attempt: int = 1) -> List[Dict[str, Any]]:
        normalized_data = []
        failures = []
        now = datetime.now()
        self.code_repo.preload()
        
        for cand in candidates:
            try:
                shop_raw = cand.get("shop", {})
                addr_cd, addr_detail = self._normalize_address(
                    shop_raw.get("full_address", ""), 
                    cand.get("entity_id")
                )
                dedup_key, dedup_key_type = self._generate_dedup_key(shop_raw, shop_raw.get("canonical_url"))
                
                store = StoreModel(
                    entity_id=cand.get("entity_id", ""),
                    entity_ref=cand.get("entity_ref", {}),
                    name=shop_raw.get("name", "Unknown"),
                    shop_cd=self.code_repo.get_shop_code(category_cd) or "UNKNOWN",
                    address_cd=addr_cd,
                    address_detail=addr_detail,
                    latitude=float(shop_raw.get("latitude", 0.0)),
                    longitude=float(shop_raw.get("longitude", 0.0)),
                    rating=float(shop_raw.get("rating", 0.0)),
                    source_platform=shop_raw.get("source_platform", ""),
                    source_internal_id=shop_raw.get("source_internal_id", ""),
                    dedup_key=dedup_key,
                    dedup_key_type=dedup_key_type,
                    canonical_url=shop_raw.get("canonical_url")
                )
                
                normalized_record = {
                    "store": store.model_dump(),
                    "menus": cand.get("menus", []),
                    "reviews": cand.get("reviews", []),
                    "images": cand.get("images", []),
                    "normalized_at": now.isoformat()
                }
                normalized_data.append(normalized_record)
                
            except Exception as e:
                self.logger.error(f"Normalization failed for {cand.get('entity_id')}: {str(e)}")
                failures.append({
                    "entity_id": cand.get("entity_id", "unknown"),
                    "entity_ref": cand.get("entity_ref", {}),
                    "status": "fail",
                    "reason_code": "INVALID_DATA_FORMAT",
                    "detail": str(e),
                    "failed_at": now.isoformat()
                })
        
        if normalized_data:
            normalized_path = HivePathBuilder.build_path(
                process="normalized", service="shop", category_cd=category_cd,
                stage=self.stage_name, batch_id=batch_id, status="success", dt=now
            )
            filename = f"{now.strftime('%y%m%d%H%M%S')}_att{run_attempt}.jsonl"
            JsonlWriter.write(normalized_path, filename, normalized_data)
            self.logger.info(f"Normalized {len(normalized_data)} records for batch {batch_id}")

        if failures:
            fail_path = HivePathBuilder.build_path(
                process="normalized", service="shop", category_cd=category_cd,
                stage=self.stage_name, batch_id=batch_id, status="fail", dt=now
            )
            filename_fail = f"{now.strftime('%y%m%d%H%M%S')}_att{run_attempt}_fail.jsonl"
            JsonlWriter.write(fail_path, filename_fail, failures)
        
        return normalized_data
