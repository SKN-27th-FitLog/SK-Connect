from common.connection import get_cursor
from common.logging_config import set_logging
import time

logger = set_logging()


def get_image(data: list[dict]) -> list:
    try:
        crawling_id = data[0]["crawling_id"]
        query = """
        SELECT i.image_url
        FROM images AS i
        JOIN "codeT" AS c
          ON c.cd = i.table_cd
         AND c.cd_upper = 'TC00'
         AND c.name = 'crawling'
        WHERE i.table_id = %s
        """
        image = get_cursor(query, (crawling_id,))
        image_list = image.fetchall() if image else []
        return image_list
    except Exception as e:
        logger.error(f"Error={e} | crawling_id = {data[0].get('crawling_id')}")


def get_similar_post(results: list[dict]) -> list[dict]:
    try:
        similar_post = []
        for result in results:
            if hasattr(result, "page_content"):
                similar_post.append(result.page_content)
            else:
                similar_post.append(result.get("content", ""))
        return similar_post
    except Exception as e:
        logger.error(
            f"get_similar_post | Error={e} | time={time.time()}"
        )
        return []

