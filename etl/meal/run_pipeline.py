import asyncio
import logging
import sys
import io
import os
from src.pipeline.orchestrator import PipelineOrchestrator

# 한글 및 로그 설정
sys.stdout = io.TextIOWrapper(sys.stdout.detach(), encoding='utf-8')
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

async def main():
    # 설정값 로드 확인
    from src.core.config import settings
    logger.info(f"\n[DEBUG] ENV LOADED -> Host: {settings.DB_HOST}, User: {settings.DB_USER}, DB: {settings.DB_NAME}\n")
    
    if not os.path.exists("target.csv"):
        logger.error("Seed file 'target.csv' not found.")
        return

    # 파이프라인 가동 (다이닝코드 플랫폼, 한식 카테고리 SC01)
    # target.csv의 category_cd와 일치해야 함.
    orchestrator = PipelineOrchestrator(platform="DiningCode")
    await orchestrator.run(category_cd="SC01")

if __name__ == "__main__":
    asyncio.run(main())
