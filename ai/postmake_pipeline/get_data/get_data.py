import time

from common.connection import get_cursor
from common.logging_config import set_logging

logger = set_logging()


def search_post(row: dict) -> dict:
    """
    analysis row의 shop_id와 posts.created_at 날짜 기준으로 이미 생성된 게시글을 조회한다.
    하루에 하나의 shop_id는 하나의 게시글만 생성한다.
    """
    try:
        query = """
        SELECT *
        FROM posts
        WHERE shop_id = %s
          AND created_at::date = CURRENT_DATE
        ORDER BY created_at DESC
        LIMIT 1
        """
        cursor = get_cursor(query, (row["shop_id"],))
        data = cursor.fetchone() if cursor else None
        if not data:
            return None
        return data

    except Exception as e:
        logger.error(f"search_post | Error={e} | time={time.time()}")
        return False


def get_data():
    """analysis 테이블에서 게시글 생성 대상 row를 가져온다."""
    try:
        query = """
        WITH last_post AS (
            SELECT shop_id, MAX(created_at) AS last_post_created_at
            FROM posts
            WHERE shop_id IS NOT NULL
            GROUP BY shop_id
        ),
        candidate_shop AS (
            SELECT a.shop_id
            FROM analysis AS a
            LEFT JOIN last_post AS p
                ON p.shop_id = a.shop_id
            WHERE a.shop_id IS NOT NULL
              AND a.created_dt < NOW() - INTERVAL '1 day'
              AND NOT EXISTS (
                  SELECT 1
                  FROM posts AS today_post
                  WHERE today_post.shop_id = a.shop_id
                    AND today_post.created_at::date = CURRENT_DATE
              )
              AND (
                  p.last_post_created_at IS NULL
                  OR a.created_dt > p.last_post_created_at
              )
            GROUP BY a.shop_id
            HAVING COUNT(*) >= 5
        )
        SELECT a.*
        FROM analysis AS a
        JOIN candidate_shop AS c
            ON c.shop_id = a.shop_id
        LEFT JOIN last_post AS p
            ON p.shop_id = a.shop_id
        WHERE a.created_dt < NOW() - INTERVAL '1 day'
          AND NOT EXISTS (
              SELECT 1
              FROM posts AS today_post
              WHERE today_post.shop_id = a.shop_id
                AND today_post.created_at::date = CURRENT_DATE
          )
          AND (
              p.last_post_created_at IS NULL
              OR a.created_dt > p.last_post_created_at
          )
        ORDER BY a.shop_id, a.created_dt DESC
        """
        cursor = get_cursor(query)
        if not cursor:
            return None
        for row in cursor.fetchall():
            yield row

    except Exception as e:
        logger.error(f"get_data | Error={e} | time={time.time()}")
        return None


def iter_shop_data():
    """get_data로 가져온 row들을 shop_id 단위로 순차 반환한다."""
    try:
        shop_data: list[dict] = []
        shop_id = None

        for data in get_data() or []:
            if shop_id is None:
                shop_id = data["shop_id"]
                shop_data.append(data)
                continue

            if shop_id != data["shop_id"]:
                yield shop_data
                shop_data = [data]
                shop_id = data["shop_id"]
                continue

            shop_data.append(data)

        if shop_data:
            yield shop_data
    except Exception as e:
        logger.error(f"iter_shop_data | Error={e} | time={time.time()}")


def get_shop_data() -> list[dict]:
    """첫 번째 shop_id 묶음을 반환한다."""
    try:
        return next(iter_shop_data(), None)
    except Exception as e:
        logger.error(f"get_shop_data | Error={e} | time={time.time()}")
        return None


def analysis_data(data: list[dict]) -> bool:
    try:
        count = 0
        for row in data:
            if count >= 5:
                return True
            elif row["sentimental"] == "positive":
                count += 1
    except Exception as e:
        logger.error(f"analysis_data | Error={e} | time={time.time()}")
        return None
