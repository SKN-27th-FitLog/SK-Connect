import glob
import logging
import os
from datetime import datetime
from typing import Any, Dict, List

from src.core.storage.jsonl_writer import JsonlWriter
from src.core.storage.path_builder import HivePathBuilder

logger = logging.getLogger("core.repository")


class FailRepository:
    def get_retry_targets(self, category_cd: str, platform: str) -> List[Dict[str, Any]]:
        dt = datetime.now()
        base_path = HivePathBuilder.build_stage_base_path(
            process="retry",
            service="shop",
            category_cd=category_cd,
            stage="fail_handling",
            status="pending",
            dt=dt,
        )
        retry_files = glob.glob(os.path.join(base_path, "batch_id=*", "status=pending", "retry_items.jsonl"))

        targets = []
        for file_path in retry_files:
            for record in JsonlWriter.read(file_path):
                metadata = record.get("metadata", {})
                entity_ref = metadata.get("entity_ref", {})
                data = record.get("data", {})

                address_cd = (
                    entity_ref.get("address_cd")
                    or data.get("address_cd")
                    or data.get("store", {}).get("address_cd")
                )
                if not address_cd:
                    logger.debug(f"Skipping retry record without address_cd: {record.get('entity_id')}")
                    continue

                target: Dict[str, Any] = {
                    "address_cd": address_cd,
                    "retry_count": metadata.get("retry_count", record.get("retry_count", 0)),
                }

                store_id = entity_ref.get("store_id") or data.get("store_id")
                article_url = (
                    entity_ref.get("article_url")
                    or data.get("article_url")
                    or data.get("store", {}).get("canonical_url")
                )
                if store_id:
                    target["store_id"] = store_id
                if article_url:
                    target["article_url"] = article_url

                targets.append(target)

        return targets
