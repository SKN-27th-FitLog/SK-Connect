import os
import glob
import logging
import argparse
from datetime import datetime
from src.core.config import settings
from src.core.registry import get_stage, STAGE_FAIL_CLASSIFICATION
from src.core.storage.jsonl_writer import JsonlWriter

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("failcheck_project")

def run_failcheck(category_cd: str):
    logger.info(f"--- Starting FAILCHECK Project ---")
    dt = datetime.now()
    stage5 = get_stage(STAGE_FAIL_CLASSIFICATION)
    
    # Search for status=fail in all processes across today's executions
    search_pattern = os.path.join(
        settings.LAKE_ROOT_PATH,
        "process=*", "service=shop",
        f"year={dt.strftime('%Y')}", f"month={dt.strftime('%m')}", f"day={dt.strftime('%d')}",
        "status=fail", f"category_cd={category_cd}", "stage=*", "batch_id=*"
    )
    
    fail_batch_dirs = glob.glob(search_pattern)
    if not fail_batch_dirs:
        logger.info("No failure directories found for today.")
        return

    batch_failures = {}
    for bdir in fail_batch_dirs:
        batch_id = os.path.basename(bdir).split("=")[-1]
        if batch_id not in batch_failures:
            batch_failures[batch_id] = []
            
        for fail_file in glob.glob(os.path.join(bdir, "*.jsonl")):
            batch_failures[batch_id].extend(JsonlWriter.read(fail_file))

    for batch_id, failures in batch_failures.items():
        if failures:
            logger.info(f"Resolving {len(failures)} failures for batch {batch_id} (determining subsequent actions)...")
            # Stage 5 internally uses PolicyResolver to decide final outcome (Action.RETRY, REPROCESS etc.)
            stage5.execute(failures, batch_id, category_cd)

    logger.info(f"--- FAILCHECK Project Finished ---")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--category", type=str, default="SC01")
    args = parser.parse_args()
    
    run_failcheck(args.category)
