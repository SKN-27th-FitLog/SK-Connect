from common.connection import get_cursor
from common.logging_config import set_logging

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

