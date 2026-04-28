import logging
from datetime import datetime
from src.core.registry import get_collector, get_stage, STAGE_TARGET_SELECTION, STAGE_RAW_COLLECTION
from src.core.utils.batch_util import BatchUtil
from src.core.config import settings

logger = logging.getLogger("crawl_project")

class CrawlService:
    @staticmethod
    async def run_crawl(platform: str, category_cd: str) -> dict:
        """
        Crawl 프로젝트 비즈니스 로직.
        Stage0(타겟 선정) -> BatchId 결정 -> Stage1(수집) 순으로 오케스트레이션 수행.
        """
        now = datetime.now()
        logger.info(f"--- Starting CRAWL Project: {platform}/{category_cd} ---")
        
        # 1. Stage 0: 타겟 선정 실행
        stage0 = get_stage(STAGE_TARGET_SELECTION)
        targets, selected_path = stage0.execute(category_cd, platform)
        
        if not targets:
            logger.info("No targets found in Stage 0. Terminating crawl.")
            return {"message": "No targets found"}
            
        # 2. Batch ID 및 Attempt 결정 (동일 타겟 재실행 시 ID 재사용)
        batch_id, run_attempt = BatchUtil.resolve_batch_id(category_cd, targets, selected_path, now)
        logger.info(f"Using Batch ID: {batch_id} [Attempt: {run_attempt}]")

        # 3. Stage 1: Shard 단위 수집 실행
        collector = get_collector(platform)
        stage1 = get_stage(STAGE_RAW_COLLECTION, collector=collector)
        
        shard_size = getattr(settings, "CRAWL_SHARD_SIZE", 10)
        shards = BatchUtil.split_targets_into_shards(targets, shard_size)
        logger.info(f"Split {len(targets)} targets into {len(shards)} shards (size={shard_size})")

        for i, shard_targets in enumerate(shards):
            shard_id = BatchUtil.generate_shard_id(batch_id, i)
            logger.info(f"Executing Shard {shard_id} ({len(shard_targets)} targets)")
            # AWS 환경에서는 이 단위가 Lambda/SQS 분리 지점이 됨
            await stage1.execute_shard(
                shard_targets=shard_targets,
                batch_id=batch_id,
                category_cd=category_cd,
                shard_id=shard_id,
                run_attempt=run_attempt
            )
        
        logger.info(f"--- CRAWL Project Finished ---")
        return {
            "batch_id": batch_id,
            "targets_processed": len(targets),
            "shards_created": len(shards),
            "run_attempt": run_attempt
        }
