import asyncio
import logging
from src.pipeline.orchestrator import PipelineOrchestrator

# 기본 로깅 설정 (설계안 20장: 개발/운영 로깅 정책 고려 가능)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def handler(event, context):
    """
    AWS Lambda 엔트리 포인트.
    설계안 5장 준수: Lambda 기반 핸들러 실행 가능 구조.
    """
    category_cd = event.get("category_cd", "CA01")
    
    logger.info(f"Lambda Triggered for category: {category_cd}")
    
    # 1. 오케스트레이터 생성
    orchestrator = PipelineOrchestrator()
    
    # 2. 비동기 실행 루프 가동
    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(orchestrator.run(category_cd))
        
        return {
            "statusCode": 200,
            "body": f"Successfully processed category {category_cd}"
        }
    except Exception as e:
        logger.error(f"Lambda Execution Error: {str(e)}")
        return {
            "statusCode": 500,
            "body": f"Error: {str(e)}"
        }

# 로컬 테스트용
if __name__ == "__main__":
    test_event = {"category_cd": "CA01"}
    handler(test_event, None)
