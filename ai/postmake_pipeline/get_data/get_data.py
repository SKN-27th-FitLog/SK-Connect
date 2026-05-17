import time

from common.connection import get_cursor
from common.logging_config import set_logging

logger = set_logging()


def search_post(row: dict) -> dict:
    """
    analysis row의 shop_id와 posts.created_at 날짜 기준으로 오늘 생성된 게시글을 조회한다.
    하루에 하나의 shop_id는 하나의 게시글만 생성한다.
    """
    try:
        # 현재 날짜에 이미 생성된 게시글이 있으면 중복 생성을 막기 위해 조회한다.
        query = """
        SELECT *
        FROM posts
        WHERE shop_id = %s
          AND created_at::date = CURRENT_DATE
        ORDER BY created_at DESC
        LIMIT 1
        """
        cursor = get_cursor(query, (row["shop_id"],))
        data = None
        if cursor:
            data = cursor.fetchone()
        if not data:
            return None
        return data

    except Exception as e:
        logger.error(f"search_post | Error={e} | time={time.time()}")
        return False


def get_data(collection_name: str = "post_vector", min_rows: int = 5, delay_days: int = 1):
    """analysis 테이블에서 게시글 생성 대상 row를 가져온다."""
    try:
        # 후보 조건:
        # 1. shop_id가 있고 하루 이상 지난 crawling 데이터
        # 2. 오늘 같은 shop_id로 생성된 게시글이 없음
        # 3. 마지막 게시글에 사용된 latest_crawling_created_at 이후 신규 row가 5개 이상
        query = """
        WITH post_vector_last AS (
            SELECT
                NULLIF(e.cmetadata ->> 'shop_id', '')::BIGINT AS shop_id,
                MAX(NULLIF(e.cmetadata ->> 'latest_crawling_created_at', '')::TIMESTAMP) AS last_crawling_created_at
            FROM langchain_pg_embedding AS e
            JOIN langchain_pg_collection AS c
                ON c.uuid = e.collection_id
            WHERE c.name = %s
              AND e.cmetadata ? 'shop_id'
              AND e.cmetadata ? 'latest_crawling_created_at'
            GROUP BY NULLIF(e.cmetadata ->> 'shop_id', '')::BIGINT
        ),
        analysis_source AS (
            SELECT
                a.*,
                COALESCE(cr.created_at, a.created_dt) AS crawling_created_at
            FROM analysis AS a
            LEFT JOIN crawling AS cr
                ON cr.crawling_id = a.crawling_id
        ),
        last_post AS (
            SELECT shop_id, MAX(created_at) AS last_post_created_at
            FROM posts
            WHERE shop_id IS NOT NULL
            GROUP BY shop_id
        ),
        candidate_shop AS (
            SELECT a.shop_id
            FROM analysis_source AS a
            LEFT JOIN last_post AS p
                ON p.shop_id = a.shop_id
            LEFT JOIN post_vector_last AS v
                ON v.shop_id = a.shop_id
            WHERE a.shop_id IS NOT NULL
              AND a.crawling_created_at < NOW() - (%s * INTERVAL '1 day')
              AND NOT EXISTS (
                  SELECT 1
                  FROM posts AS today_post
                  WHERE today_post.shop_id = a.shop_id
                    AND today_post.created_at::date = CURRENT_DATE
              )
              AND (
                  COALESCE(v.last_crawling_created_at, p.last_post_created_at) IS NULL
                  OR a.crawling_created_at > COALESCE(v.last_crawling_created_at, p.last_post_created_at)
              )
            GROUP BY a.shop_id
            HAVING COUNT(*) >= %s
        )
        SELECT a.*
        FROM analysis_source AS a
        JOIN candidate_shop AS c
            ON c.shop_id = a.shop_id
        LEFT JOIN last_post AS p
            ON p.shop_id = a.shop_id
        LEFT JOIN post_vector_last AS v
            ON v.shop_id = a.shop_id
        WHERE a.crawling_created_at < NOW() - (%s * INTERVAL '1 day')
          AND NOT EXISTS (
              SELECT 1
              FROM posts AS today_post
              WHERE today_post.shop_id = a.shop_id
                AND today_post.created_at::date = CURRENT_DATE
          )
          AND (
              COALESCE(v.last_crawling_created_at, p.last_post_created_at) IS NULL
              OR a.crawling_created_at > COALESCE(v.last_crawling_created_at, p.last_post_created_at)
          )
        ORDER BY a.shop_id, a.crawling_created_at DESC
        """
        cursor = get_cursor(query, (collection_name, delay_days, min_rows, delay_days))
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

        # SQL 정렬이 shop_id 기준이므로, shop_id가 바뀌는 순간 이전 묶음을 반환한다.
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

        # 마지막 shop_id 묶음은 루프 종료 후 별도로 반환한다.
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
    """긍정 분석 데이터가 5개 이상인지 확인한다."""
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
