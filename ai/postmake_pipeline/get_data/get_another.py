from common.connection import get_cursor
from common.logging_config import set_logging
import time

logger = set_logging()


def get_image(data: list[dict], image_table: str = "shop") -> list:
    """매장(shop)에 연결된 이미지 URL 목록을 조회한다."""
    try:
        shop_id = data[0]["shop_id"]
        column_query = """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = %s
          AND column_name IN (%s, %s)
        """
        column_cursor = get_cursor(column_query, ("images", "table_name", "table_cd"))
        columns = set()
        if column_cursor:
            columns = {row["column_name"] for row in column_cursor.fetchall()}
        table_column = "table_cd"
        if "table_name" in columns:
            table_column = "table_name"

        # DB 초기화 경로에 따라 images의 구분 컬럼명이 table_name 또는 table_cd일 수 있다.
        query = f"""
        SELECT i.image_url
        FROM images AS i
        WHERE i.{table_column} = %s
          AND i.table_id = %s
        """
        image = get_cursor(query, (image_table, shop_id))
        image_list = []
        if image:
            image_list = image.fetchall()
        return image_list
    except Exception as e:
        logger.error(f"Error={e} | crawling_id = {data[0].get('crawling_id')}")


def get_similar_post(results: list[dict]) -> list[dict]:
    """벡터 검색 결과에서 게시글 본문만 추출해 재생성 프롬프트에 넘긴다."""
    try:
        similar_post = []
        for result in results:
            if hasattr(result, "page_content"):
                similar_post.append(result.page_content)
                continue
            similar_post.append(result.get("content", ""))
        return similar_post
    except Exception as e:
        logger.error(
            f"get_similar_post | Error={e} | time={time.time()}"
        )
        return []

