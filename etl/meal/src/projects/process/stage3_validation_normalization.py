import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from src.core.base_stage import BaseStage
from src.core.repository.code_table_repository import CodeTableRepository
from src.core.storage.path_builder import HivePathBuilder
from src.core.storage.jsonl_writer import JsonlWriter
from src.core.models.models import StoreModel
from src.core.repository.store_repository import StoreRepository
from src.core.policy.fail_record import build_fail_record
from src.core.policy.reason_code import ReasonCode
from src.core.utils.content_hash import (
    HASH_FIELDS_VERSION,
    HASH_VERSION,
    build_content_hash,
    pick_fields,
)

class Stage3ValidationNormalization(BaseStage):
    """
    [요구사항 2.2, 7.2, 10 일치] - Validation & Normalization Stage.
    데이터 정규화, 주소 코드 분리, Dedup Key 생성 수행.
    """
    NAME = "validation_normalization"

    def __init__(
        self,
        code_repository: CodeTableRepository | None = None,
        snapshot_repository: StoreRepository | None = None,
    ):
        super().__init__(self.NAME)
        self.code_repo = code_repository or CodeTableRepository()
        self.snapshot_repo = snapshot_repository or StoreRepository()

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

    def _build_entity_hashes(
        self,
        store: StoreModel,
        menus: List[Dict[str, Any]],
        reviews: List[Dict[str, Any]],
        images: List[Any],
    ) -> Dict[str, str]:
        store_data = store.model_dump()
        image_urls = [img.get("url") if isinstance(img, dict) else img for img in images]
        review_summary = {
            "review_count": len(reviews),
            "rating": store_data.get("rating"),
            "latest_review_at": max(
                (review.get("visited_at") for review in reviews if review.get("visited_at")),
                default=None,
            ),
        }

        return {
            "store_content_hash": build_content_hash(
                pick_fields(
                    {
                        **store_data,
                        "normalized_name": store_data.get("name"),
                        "normalized_address": f"{store_data.get('address_cd')} {store_data.get('address_detail')}",
                        "phone": store_data.get("phone"),
                        "opening_hours": store_data.get("opening_hours"),
                    },
                    ["normalized_name", "normalized_address", "phone", "opening_hours", "canonical_url"],
                )
            ),
            "menu_content_hash": build_content_hash(
                [
                    pick_fields(menu, ["menu_name", "name", "price", "description"])
                    for menu in menus
                ]
            ),
            "review_content_hash": build_content_hash(review_summary),
            "image_content_hash": build_content_hash(image_urls),
        }

    def _build_change_fields(self, dedup_key: str, current_hashes: Dict[str, str], snapshot_map: Dict[str, Any] | None = None) -> Dict[str, Any]:
        snapshot = (snapshot_map or {}).get(dedup_key) or {}
        previous_hashes = {
            "previous_store_content_hash": snapshot.get("store_content_hash"),
            "previous_menu_content_hash": snapshot.get("menu_content_hash"),
            "previous_review_content_hash": snapshot.get("review_content_hash"),
            "previous_image_content_hash": snapshot.get("image_content_hash"),
        }
        changed = {
            "store_changed": current_hashes["store_content_hash"] != previous_hashes["previous_store_content_hash"],
            "menu_changed": current_hashes["menu_content_hash"] != previous_hashes["previous_menu_content_hash"],
            "review_changed": current_hashes["review_content_hash"] != previous_hashes["previous_review_content_hash"],
            "image_changed": current_hashes["image_content_hash"] != previous_hashes["previous_image_content_hash"],
        }
        return {
            **current_hashes,
            **previous_hashes,
            "existing_store_id": snapshot.get("store_id"),
            "existing_map_id": snapshot.get("map_id"),
            **changed,
            "is_changed": any(changed.values()),
            "changed_fields": [key.removesuffix("_changed") for key, value in changed.items() if value],
            "hash_version": HASH_VERSION,
            "hash_fields_version": HASH_FIELDS_VERSION,
        }

    def execute(self, candidates: List[Dict[str, Any]], batch_id: str, category_cd: str, run_attempt: int = 1) -> List[Dict[str, Any]]:
        normalized_data = []
        failures = []
        now = datetime.now()
        self.code_repo.preload()

        dedup_keys = []
        for cand in candidates:
            shop_raw = cand.get("shop", {})
            key, _ = self._generate_dedup_key(shop_raw, shop_raw.get("canonical_url"))
            dedup_keys.append(key)
        snapshot_map = self.snapshot_repo.bulk_find_snapshots(dedup_keys)

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
                
                menus = cand.get("menus", [])
                reviews = cand.get("reviews", [])
                images = cand.get("images", [])
                hash_fields = self._build_change_fields(
                    dedup_key,
                    self._build_entity_hashes(store, menus, reviews, images),
                    snapshot_map,
                )

                normalized_record = {
                    "batch_id": batch_id,
                    "run_attempt": run_attempt,
                    "stage": self.stage_name,
                    "category_cd": category_cd,
                    "store": store.model_dump(),
                    "menus": menus,
                    "reviews": reviews,
                    "images": images,
                    **hash_fields,
                    "normalized_at": now.isoformat()
                }
                normalized_data.append(normalized_record)
                
            except Exception as e:
                self.logger.error(f"Normalization failed for {cand.get('entity_id')}: {str(e)}")
                failures.append(build_fail_record(
                    batch_id=batch_id,
                    run_attempt=run_attempt,
                    stage=self.stage_name,
                    entity_type="store",
                    entity_id=cand.get("entity_id", "unknown"),
                    entity_ref=cand.get("entity_ref", {}),
                    reason_code=ReasonCode.INVALID_DATA_FORMAT,
                    detail=str(e),
                    created_at=now,
                ))
        
        if normalized_data:
            normalized_path = HivePathBuilder.build_path(
                process="normalized", service="shop", category_cd=category_cd,
                stage=self.stage_name, batch_id=batch_id, status="success", dt=now
            )
            filename = HivePathBuilder.build_filename(
                "jsonl", now, stage=self.stage_name, batch_id=batch_id, run_attempt=run_attempt
            )
            JsonlWriter.write(normalized_path, filename, normalized_data)
            self.logger.info(f"Normalized {len(normalized_data)} records for batch {batch_id}")

        if failures:
            fail_path = HivePathBuilder.build_path(
                process="normalized", service="shop", category_cd=category_cd,
                stage=self.stage_name, batch_id=batch_id, status="fail", dt=now
            )
            filename_fail = HivePathBuilder.build_filename(
                "jsonl", now, stage=self.stage_name, batch_id=batch_id, run_attempt=run_attempt, suffix="fail"
            )
            JsonlWriter.write(fail_path, filename_fail, failures)
        
        if hasattr(self.code_repo, "clear_cache"):
            self.code_repo.clear_cache()
        return normalized_data
