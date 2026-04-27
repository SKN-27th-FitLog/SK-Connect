import logging
from typing import Any, Dict, Optional, Set

from sqlalchemy import text

from src.core.repository.database import DatabaseManager
from src.core.constants import find_success_loaded_dedup_keys
from src.core.constants import find_update_targets
from src.core.constants import find_snapshot_by_dedup_key

logger = logging.getLogger("core.repository")


class StoreRepository:
    def __init__(self, db: DatabaseManager | None = None):
        self.db = db or DatabaseManager()

    def find_success_loaded_dedup_keys(self, category_cd: str) -> Set[str]:
        query = constants.find_success_loaded_dedup_keys
        dedup_keys = set()
        try:
            with self.db.get_session() as session:
                result = session.execute(text(query), {"category_cd": category_cd})
                for row in result:
                    name = row.name.replace(" ", "")
                    dedup_keys.add(f"{name}|{row.address_cd}")
        except Exception as e:
            logger.error(f"Failed to fetch success loaded dedup keys: {e}")
        return dedup_keys

    def is_duplicated(self, target_dedup_key: str, existing_keys: Set[str]) -> bool:
        return target_dedup_key in existing_keys

    def find_update_targets(self, category_cd: str, limit: int, refresh_interval_days: int = 30) -> list[Dict[str, Any]]:
        query = constants.find_update_targets
        try:
            with self.db.get_session() as session:
                rows = session.execute(text(query), {
                    "category_cd": category_cd,
                    "refresh_interval_days": refresh_interval_days,
                    "limit": limit,
                }).mappings().all()
                return [dict(row) for row in rows]
        except Exception as e:
            logger.debug(f"Failed to fetch update targets: {e}")
            return []

    def find_snapshot_by_dedup_key(self, dedup_key: str) -> Optional[Dict[str, Any]]:
        query = constants.find_snapshot_by_dedup_key
        try:
            with self.db.get_session() as session:
                row = session.execute(text(query), {"dedup_key": dedup_key}).mappings().first()
                return dict(row) if row else None
        except Exception as e:
            logger.debug(f"Snapshot hash lookup skipped for dedup_key={dedup_key}: {e}")
            return None
