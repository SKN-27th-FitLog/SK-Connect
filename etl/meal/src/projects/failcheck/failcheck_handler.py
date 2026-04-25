import logging
import argparse
from src.projects.failcheck.failcheck_service import FailcheckService

# 로깅 설정
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("failcheck_project")

def lambda_handler(event, context):
    """
    AWS Lambda 엔트리 포인트. 핸들러는 단순 입력 파싱 및 Service 호출 역할만 수행.
    """
    category_cd = event.get("category_cd")
    
    if not category_cd:
        return {
            "statusCode": 400,
            "body": {"error": "Missing mandatory parameter: category_cd"}
        }
    
    logger.info(f"Event received - Category: {category_cd}")
    
    try:
        # Failcheck는 오로지 '파일 이동 및 판단'만 수행하므로 매우 가벼움
        result = FailcheckService.run_failcheck(category_cd)
    except Exception as e:
        logger.error(f"Failcheck project failed with error: {str(e)}", exc_info=True)
        return {
            "statusCode": 500,
            "body": {"error": str(e)}
        }
    
    return {
        "statusCode": 200,
        "body": result
    }

if __name__ == "__main__":
    # 로컬 실행 지원
    parser = argparse.ArgumentParser()
    parser.add_argument("--category", type=str, required=True, help="Category Code (e.g., C001)")
    args = parser.parse_args()
    
    result = lambda_handler({"category_cd": args.category}, None)
    logger.info(f"Local Execution Result: {result}")
