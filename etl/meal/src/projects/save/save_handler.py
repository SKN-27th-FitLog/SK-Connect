import logging
import argparse
from src.projects.save.save_service import SaveService

# 로깅 설정
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("save_project")

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
        result = SaveService.run_save(category_cd)
    except Exception as e:
        logger.error(f"Save project failed with error: {str(e)}", exc_info=True)
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
