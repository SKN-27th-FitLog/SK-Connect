import asyncio
import logging
import argparse
from src.projects.crawl.crawl_service import CrawlService

# 로깅 설정
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("crawl_project")

def lambda_handler(event, context):
    """
    AWS Lambda 엔트리 포인트. 핸들러는 단순 입력 파싱 및 Service 호출 역할만 수행.
    """
    platform = event.get("platform")
    category_cd = event.get("category_cd")
    
    if not platform or not category_cd:
        return {
            "statusCode": 400,
            "body": {"error": "Missing mandatory parameters: platform, category_cd"}
        }
    
    logger.info(f"Event received - Platform: {platform}, Category: {category_cd}")
    
    # Lambda 환경에서는 이미 loop가 돌고 있을 수 있으므로 안전하게 새 루프 생성 및 제어
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(CrawlService.run_crawl(platform, category_cd))
    except Exception as e:
        logger.error(f"Crawl project failed with error: {str(e)}", exc_info=True)
        return {
            "statusCode": 500,
            "body": {"error": str(e)}
        }
    finally:
        loop.close()
    
    return {
        "statusCode": 200,
        "body": result
    }

if __name__ == "__main__":
    # 로컬 실행 지원
    parser = argparse.ArgumentParser()
    parser.add_argument("--platform", type=str, required=True, help="Target Platform (Naver, DiningCode, etc)")
    parser.add_argument("--category", type=str, required=True, help="Category Code (e.g., C001)")
    args = parser.parse_args()
    
    result = lambda_handler({"platform": args.platform, "category_cd": args.category}, None)
    logger.info(f"Local Execution Result: {result}")
