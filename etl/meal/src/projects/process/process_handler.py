import os
import glob
import logging
import argparse
from datetime import datetime
from src.core.config import settings
from src.core.registry import get_parser, get_stage, STAGE_CANDIDATE_PARSING, STAGE_VALIDATION_NORMALIZATION
from src.core.storage.jsonl_writer import JsonlWriter

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("process_project")

def run_process(platform: str, category_cd: str):
    logger.info(f"--- Starting PROCESS Project ---")
    dt = datetime.now()
    
    base_path = os.path.join(
        settings.LAKE_ROOT_PATH,
        "process=raw", "service=shop",
        f"year={dt.strftime('%Y')}", f"month={dt.strftime('%m')}", f"day={dt.strftime('%d')}",
        "status=success", f"category_cd={category_cd}", "stage=raw_collection"
    )
    
    batch_dirs = glob.glob(os.path.join(base_path, "batch_id=*"))
    if not batch_dirs:
        logger.info("No crawl success data found for today. Terminating process.")
        return

    parser = get_parser(platform)
    stage2 = get_stage(STAGE_CANDIDATE_PARSING, parser=parser)
    stage3 = get_stage(STAGE_VALIDATION_NORMALIZATION)

    for bdir in batch_dirs:
        batch_id = os.path.basename(bdir).split("=")[-1]
        raw_successes = []
        for file in glob.glob(os.path.join(bdir, "*.jsonl")):
            raw_successes.extend(JsonlWriter.read(file))
            
        if not raw_successes: continue
        
        candidates = stage2.execute(raw_successes, batch_id, category_cd)
        if candidates:
            stage3.execute(candidates, batch_id, category_cd)

    logger.info(f"--- PROCESS Project Finished ---")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--platform", type=str, default="DiningCode")
    parser.add_argument("--category", type=str, default="SC01")
    args = parser.parse_args()
    
    run_process(args.platform, args.category)
