import asyncio
import logging
import argparse
from datetime import datetime
from src.core.registry import get_collector, get_stage, STAGE_TARGET_SELECTION, STAGE_RAW_COLLECTION

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("crawl_project")

async def run_crawl(platform: str, category_cd: str):
    now = datetime.now()
    batch_id = f"{now.strftime('%Y%m%d')}_{category_cd}_{now.strftime('%H%M%S')}"
    logger.info(f"--- Starting CRAWL Project: {platform}/{category_cd} [Batch: {batch_id}] ---")
    
    stage0 = get_stage(STAGE_TARGET_SELECTION)
    targets = stage0.execute(category_cd, platform)
    
    if not targets:
        logger.info("No targets found in Stage 0. Terminating crawl.")
        return
        
    collector = get_collector(platform)
    stage1 = get_stage(STAGE_RAW_COLLECTION, collector=collector, shard_size=1)
    
    await stage1.execute(targets, batch_id, category_cd)
    logger.info(f"--- CRAWL Project Finished ---")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--platform", type=str, default="DiningCode")
    parser.add_argument("--category", type=str, default="SC01")
    args = parser.parse_args()
    
    asyncio.run(run_crawl(args.platform, args.category))
