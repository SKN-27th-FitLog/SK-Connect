import os
import glob
import logging
import argparse
from datetime import datetime
from src.core.config import settings
from src.core.registry import get_stage, STAGE_LOAD
from src.core.storage.path_builder import HivePathBuilder
from src.core.storage.jsonl_writer import JsonlWriter

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("save_project")

def run_save(category_cd: str):
    logger.info(f"--- Starting SAVE Project ---")
    dt = datetime.now()
    
    base_path = os.path.join(
        settings.LAKE_ROOT_PATH,
        "process=normalized", "service=shop",
        f"year={dt.strftime('%Y')}", f"month={dt.strftime('%m')}", f"day={dt.strftime('%d')}",
        "status=success", f"category_cd={category_cd}", "stage=validation_normalization"
    )
    
    batch_dirs = glob.glob(os.path.join(base_path, "batch_id=*"))
    if not batch_dirs:
        logger.info("No normalized success data found for today. Terminating load.")
        return

    stage4 = get_stage(STAGE_LOAD)

    for bdir in batch_dirs:
        batch_id = os.path.basename(bdir).split("=")[-1]
        normalized_data = []
        for norm_file in glob.glob(os.path.join(bdir, "*.jsonl")):
            normalized_data.extend(JsonlWriter.read(norm_file))
            
        if normalized_data:
            results = stage4.execute(normalized_data, batch_id, category_cd)
            successes = [r for r in results if r["status"] == "success"]
            failures = [r for r in results if r["status"] == "fail"]
            
            filename = HivePathBuilder.build_filename(extension="jsonl", dt=dt)
            
            if successes:
                succ_path = HivePathBuilder.build_path(
                    process="load", service="shop", category_cd=category_cd,
                    stage="load", batch_id=batch_id, status="success", dt=dt
                )
                JsonlWriter.write(succ_path, filename, successes)
                
            if failures:
                fail_path = HivePathBuilder.build_path(
                    process="load", service="shop", category_cd=category_cd,
                    stage="load", batch_id=batch_id, status="fail", dt=dt
                )
                JsonlWriter.write(fail_path, filename, failures)
            
    logger.info(f"--- SAVE Project Finished ---")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--category", type=str, default="SC01")
    args = parser.parse_args()
    
    run_save(args.category)
