import logging
from typing import Any, Dict, Optional, Set

from sqlalchemy import text

from src.core.repository.database import DatabaseManager
from src.core.constants import (
    QUERY_BULK_FIND_SNAPSHOTS,
    QUERY_FIND_SNAPSHOT_BY_DEDUP_KEY,
    QUERY_FIND_SUCCESS_LOADED_DEDUP_KEYS,
    QUERY_FIND_UPDATE_TARGETS,
    RESTAURANT_CATEGORY_CD,
)

logger = logging.getLogger("core.repository")


class StoreRepository:
    def __init__(self, db: DatabaseManager | None = None):
        self.db = db or DatabaseManager()

    def find_success_loaded_dedup_keys(self, category_cd: str) -> Set[str]:
        shop_cd = category_cd
        query = QUERY_FIND_SUCCESS_LOADED_DEDUP_KEYS
        dedup_keys = set()
        try:
            with self.db.get_session() as session:
                result = session.execute(text(query), {
                    "category_cd": RESTAURANT_CATEGORY_CD,
                    "shop_cd": shop_cd,
                })
                for row in result:
                    name = row.name.replace(" ", "")
                    dedup_keys.add(f"{name}|{row.address_cd}")
        except Exception as e:
            logger.error(f"Failed to fetch success loaded dedup keys: {e}")
        return dedup_keys

    def is_duplicated(self, target_dedup_key: str, existing_keys: Set[str]) -> bool:
        return target_dedup_key in existing_keys

    def find_update_targets(self, category_cd: str, limit: int, refresh_interval_days: int = 30) -> list[Dict[str, Any]]:
        shop_cd = category_cd
        query = QUERY_FIND_UPDATE_TARGETS
        try:
            with self.db.get_session() as session:
                rows = session.execute(text(query), {
                    "category_cd": RESTAURANT_CATEGORY_CD,
                    "shop_cd": shop_cd,
                    "refresh_interval_days": refresh_interval_days,
                    "limit": limit,
                }).mappings().all()
                return [dict(row) for row in rows]
        except Exception as e:
            logger.debug(f"Failed to fetch update targets: {e}")
            return []

    def bulk_find_snapshots(self, dedup_keys: list) -> Dict[str, Any]:
        if not dedup_keys:
            return {}
        query = QUERY_BULK_FIND_SNAPSHOTS
        snapshot_map: Dict[str, Any] = {}
        try:
            with self.db.get_session() as session:
                rows = session.execute(text(query), {"dedup_keys": dedup_keys}).mappings().all()
                dedup_keys_set = set(dedup_keys)
                for row in rows:
                    row_dict = dict(row)
                    article_url = row_dict.get("article_url")
                    name = (row_dict.get("name") or "").replace(" ", "")
                    address_cd = row_dict.get("address_cd", "")
                    name_address_key = f"{name}|{address_cd}"
                    if article_url and article_url in dedup_keys_set:
                        snapshot_map[article_url] = row_dict
                    if name_address_key in dedup_keys_set:
                        snapshot_map[name_address_key] = row_dict
        except Exception as e:
            logger.debug(f"Bulk snapshot lookup failed: {e}")
        return snapshot_map

    def find_snapshot_by_dedup_key(self, dedup_key: str) -> Optional[Dict[str, Any]]:
        query = QUERY_FIND_SNAPSHOT_BY_DEDUP_KEY
        try:
            with self.db.get_session() as session:
                row = session.execute(text(query), {"dedup_key": dedup_key}).mappings().first()
                return dict(row) if row else None
        except Exception as e:
            logger.debug(f"Snapshot hash lookup skipped for dedup_key={dedup_key}: {e}")
            return None
