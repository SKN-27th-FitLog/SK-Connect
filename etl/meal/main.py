import asyncio
import logging
import sys
import os

# src 경로 추가
sys.path.append(os.path.join(os.getcwd(), "src"))

from src.pipeline.orchestrator import PipelineOrchestrator

# 로그 설정 (설계안 20: 개발 단계 로그)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("main")

async def main():
    """
    V4 파이프라인 로컬 실행 스크립트.
    """
    logger.info("Starting Meal ETL Pipeline V4 Rewrite Verification...")
    
    # 1. 오케스트레이터 초기화
    orchestrator = PipelineOrchestrator()
    
    # 2. 실행 (테스트용 카테고리 CA01)
    try:
        # 실제 DB에 데이터가 있어야 Stage 0에서 대상이 선정됩니다.
        # 데이터가 없을 경우 "No targets selected" 로그와 함께 정상 종료됩니다.
        await orchestrator.run(category_cd="CA01")
        
    except Exception as e:
        logger.error(f"Pipeline execution failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
