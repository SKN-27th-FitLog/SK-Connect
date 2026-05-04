from common.logging_config import set_logging
import time
logger = set_logging()

def get_similar_post(results: list[dict]) -> list[dict]:
    try:
        similar_post = []
        for result in results:
            similar_post.append(result['content'])
        return similar_post
    except Exception as e:
        logger.error(f"get_similar_post | Error={e} | time={time.time() | results['crawling_id']}")
        return []