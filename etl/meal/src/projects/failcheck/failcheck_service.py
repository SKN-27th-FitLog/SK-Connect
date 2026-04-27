import glob
import logging
import os
from datetime import datetime

from src.core.dispatch import Dispatcher
from src.core.policy.resolver import Action, create_policy_resolver
from src.core.storage.jsonl_writer import JsonlWriter
from src.core.storage.path_builder import HivePathBuilder

logger = logging.getLogger("failcheck_project")


class FailcheckService:
    @staticmethod
    def _resolve_action(record: dict, date_str: str, resolver=None) -> str | None:
        resolver = resolver or create_policy_resolver()
        retry_count = record.get("retry_count", 0)
        if record.get("last_retry_date") == date_str:
            logger.info(f"Skipping record {record.get('target_id')} - Already retried today.")
            return None

        reason_code = record.get("reason_code", "UNKNOWN_ERROR")
        stage_val = record.get("stage", "unknown")
        resolution = resolver.resolve(reason_code, stage_val, retry_count)
        return resolution.name if isinstance(resolution, Action) else str(resolution)

    @staticmethod
    def run_failcheck(category_cd: str) -> dict:
        logger.info(f"--- Starting FAILCHECK Project: {category_cd} ---")
        dt = datetime.now()
        date_str = dt.strftime("%Y%m%d")

        fail_files = []
        for stage_name in ["raw_collection", "candidate_parsing", "validation_normalization", "load"]:
            process_type = "raw" if stage_name == "raw_collection" else (
                "load" if stage_name == "load" else "normalized"
            )
            base_fail_path = HivePathBuilder.build_stage_base_path(
                process=process_type,
                service="shop",
                category_cd=category_cd,
                stage=stage_name,
                status="fail",
                dt=dt,
            )
            fail_files.extend(glob.glob(os.path.join(base_fail_path, "batch_id=*", "*.jsonl")))

        if not fail_files:
            logger.info("No failed records found for today.")
            return {"message": "No failed records found"}

        failed_records = []
        for file in fail_files:
            failed_records.extend(JsonlWriter.read(file))

        logger.info(f"Gathered {len(failed_records)} failed records. Deciding follow-up actions.")

        for record in failed_records:
            action = FailcheckService._resolve_action(record, date_str)
            if action is None:
                continue

            if action in ("RETRY", "REPROCESS"):
                record["last_retry_date"] = date_str
            elif action == "DROP":
                record["final_action"] = "DROP"
                record["dropped_at"] = dt.isoformat()

            Dispatcher.dispatch(action, record, dt)

        processed_batches = list({r.get("batch_id") for r in failed_records if r.get("batch_id")})

        logger.info("--- FAILCHECK Project Finished ---")
        return {
            "processed_batches": processed_batches,
            "records_processed": len(failed_records),
        }
