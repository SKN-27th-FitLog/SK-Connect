from src.logging_config import set_logging
logger = set_logging()

def evaluate_result(result:dict) -> bool:
    """결과를 평가"""
    try:
        return result.get("status") == "passed"
    except Exception as e:
        logger.error(f"Error={e} | crawling_id={result['data']['crawling_id']}")
        return False
