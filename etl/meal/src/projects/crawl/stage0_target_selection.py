import logging
from datetime import datetime
from typing import Any, Dict, List, Set

from src.core.base_stage import BaseStage
from src.core.repository.code_table_repository import CodeTableRepository
from src.core.repository.fail_repository import FailRepository
from src.core.repository.source_pool_provider import SourcePoolProvider
from src.core.repository.store_repository import StoreRepository
from src.core.constants import QUERY_SELECT_ALL_ADDRESS_CODES


class Stage0TargetSelection(BaseStage):
    NAME = "target_selection"

    def __init__(
        self,
        code_repo: CodeTableRepository | None = None,
        store_repo: StoreRepository | None = None,
        fail_repo: FailRepository | None = None,
        source_pool: SourcePoolProvider | None = None,
        target_count: int = 100,
        update_daily_quota: int = 100,
        now: datetime | None = None,
    ):
        super().__init__(self.NAME)
        self.code_repo = code_repo or CodeTableRepository()
        self.store_repo = store_repo or StoreRepository()
        self.fail_repo = fail_repo or FailRepository()
        self.source_pool = source_pool or SourcePoolProvider()
        self.target_count = target_count
        self.update_daily_quota = update_daily_quota
        self.now = now
        self.logger = logging.getLogger(self.__class__.__name__)

    def execute(self, category_cd: str, platform: str = "DiningCode") -> tuple[List[Dict[str, Any]], str]:
        self.code_repo.preload()
        selected_targets = []

        existing_keys: Set[str] = self.store_repo.find_success_loaded_dedup_keys(category_cd)
        self.logger.info(f"Loaded {len(existing_keys)} existing dedup keys for {category_cd}")

        retry_pool = self.fail_repo.get_retry_targets(category_cd, platform)
        for item in retry_pool:
            if len(selected_targets) >= self.target_count:
                break
            selected_targets.append(self._build_target_item(item, category_cd, platform, target_type="RETRY"))

        update_limit = min(self.update_daily_quota, self.target_count - len(selected_targets))
        if update_limit > 0:
            update_pool = self.store_repo.find_update_targets(category_cd, update_limit)
            for item in update_pool:
                if len(selected_targets) >= self.target_count:
                    break
                selected_targets.append(self._build_target_item(
                    item,
                    category_cd,
                    platform,
                    target_type="UPDATE",
                    update_reason="SCHEDULED_REFRESH",
                ))

        if len(selected_targets) < self.target_count:
            candidates = self.source_pool.get_candidates(category_cd)
            for cand in candidates:
                if len(selected_targets) >= self.target_count:
                    break

                addr_cd = cand["address_cd"]
                addr_info = self.code_repo.get_address_info(addr_cd)
                if not addr_info:
                    continue

                candidate_key = f"{addr_info['name'].replace(' ', '')}|{addr_cd}"
                if self.store_repo.is_duplicated(candidate_key, existing_keys):
                    continue

                selected_targets.append(self._build_target_item(cand, category_cd, platform, target_type="NEW"))

        self.logger.info(f"Final targeting complete: {len(selected_targets)} items for Stage 1.")
        if hasattr(self.code_repo, "clear_cache"):
            self.code_repo.clear_cache()
        return selected_targets, self.source_pool.seed_file

    def _build_target_item(
        self,
        source: Dict[str, Any],
        category_cd: str,
        platform: str,
        target_type: str = "NEW",
        update_reason: str | None = None,
    ) -> Dict[str, Any]:
        addr_cd = source.get("address_cd", source.get("raw_info", {}).get("address_cd"))
        addr_info = self.code_repo.get_address_info(addr_cd)
        shop_info_name = self.code_repo.get_shop_code_name(category_cd)

        item = {
            "address_cd": addr_cd,
            "category_cd": category_cd,
            "address_name": addr_info["name"] if addr_info else "Unknown",
            "category_name": shop_info_name or "Unknown",
            "source_platform": platform,
            "search_query": f"{addr_info['name'] if addr_info else ''} {shop_info_name or ''}".strip(),
            "is_retry": target_type == "RETRY",
            "target_type": target_type,
            "retry_count": source.get("retry_count", 0),
        }
        if update_reason:
            item["update_reason"] = update_reason
        if source.get("store_id"):
            item["store_id"] = source["store_id"]
        return item
