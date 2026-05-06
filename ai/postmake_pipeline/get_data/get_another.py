from common.connection import get_cursor
from common.logging_config import set_logging
import time

logger = set_logging()


def get_image(data: list[dict]) -> list:
    try:
        map_id = data[0]["map_id"]
        query = """
        SELECT i.image_url
        FROM analysis AS a
        JOIN images AS i
            ON i.shop_id = a.shop_id
        WHERE a.shop_id = %s
        """
        image = get_cursor(query, map_id)
        image_list = image.fetchall()
        return image_list
    except Exception as e:
        logger.error(f"Error={e} | crawling_id = {data['crawling_id']}")


def get_similar_post(results: list[dict]) -> list[dict]:
    try:
        similar_post = []
        for result in results:
            similar_post.append(result["content"])
        return similar_post
    except Exception as e:
        logger.error(
            f"get_similar_post | Error={e} | time={time.time() | results['crawling_id']}"
        )
        return []

