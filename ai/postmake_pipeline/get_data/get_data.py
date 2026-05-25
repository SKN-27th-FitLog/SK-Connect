import time

from common.connection import get_cursor
from common.constants import (
    CRAWLING_IMAGE_TABLE_CD,
    RESTAURANT_INFORMATION_CD,
    SHOP_IMAGE_TABLE_CD,
)
from common.logging_config import set_logging

logger = set_logging()


def get_data(min_rows: int = 5, delay_days: int = 1):
    try:
        query = f"""
            WITH normalized_analysis AS (
                SELECT
                    a.crawling_id,
                    COALESCE(NULLIF(BTRIM(a.title), ''), NULLIF(BTRIM(cr.title), '')) AS title,
                    COALESCE(NULLIF(BTRIM(a.content), ''), NULLIF(BTRIM(cr.content), '')) AS content,
                    COALESCE(NULLIF(BTRIM(a.article_url), ''), NULLIF(BTRIM(cr.article_url), '')) AS article_url,
                    COALESCE(a_map.map_id, cr_map.map_id) AS map_id,
                    s.shop_id,
                    COALESCE(NULLIF(BTRIM(a.category_cd), ''), NULLIF(BTRIM(cr.category_cd), '')) AS category_cd,
                    COALESCE(NULLIF(BTRIM(a.information_cd), ''), NULLIF(BTRIM(cr.information_cd), '')) AS information_cd,
                    COALESCE(NULLIF(BTRIM(a.shop_cd), ''), NULLIF(BTRIM(cr.shop_cd), '')) AS shop_cd,
                    a.created_dt,
                    CASE
                        WHEN COALESCE(NULLIF(BTRIM(a.information_cd), ''), NULLIF(BTRIM(cr.information_cd), '')) = '{RESTAURANT_INFORMATION_CD}'
                            THEN a.sentimental
                        ELSE COALESCE(NULLIF(BTRIM(a.sentimental), ''), 'positive')
                    END AS sentimental,
                    CASE
                        WHEN COALESCE(NULLIF(BTRIM(a.information_cd), ''), NULLIF(BTRIM(cr.information_cd), '')) = '{RESTAURANT_INFORMATION_CD}'
                            THEN a.score
                        ELSE COALESCE(a.score, cr.point, 1.0)
                    END AS score,
                    COALESCE(NULLIF(BTRIM(a.keywords), ''), NULLIF(BTRIM(cr.keywords), '')) AS keywords,
                    COALESCE(cr.created_at, a.created_dt) AS crawling_created_at
                FROM analysis AS a
                LEFT JOIN crawling AS cr
                    ON cr.crawling_id = a.crawling_id
                LEFT JOIN maps AS a_map
                    ON a_map.map_id = a.map_id
                LEFT JOIN maps AS cr_map
                    ON cr_map.map_id = cr.map_id
                LEFT JOIN shop AS s
                    ON s.shop_id = a.shop_id
            ),
            crawling_only AS (
                SELECT
                    cr.crawling_id,
                    NULLIF(BTRIM(cr.title), '') AS title,
                    NULLIF(BTRIM(cr.content), '') AS content,
                    NULLIF(BTRIM(cr.article_url), '') AS article_url,
                    cr_map.map_id,
                    NULL::BIGINT AS shop_id,
                    NULLIF(BTRIM(cr.category_cd), '') AS category_cd,
                    NULLIF(BTRIM(cr.information_cd), '') AS information_cd,
                    NULLIF(BTRIM(cr.shop_cd), '') AS shop_cd,
                    cr.created_at AS created_dt,
                    'positive' AS sentimental,
                    COALESCE(cr.point, 1.0) AS score,
                    NULLIF(BTRIM(cr.keywords), '') AS keywords,
                    cr.created_at AS crawling_created_at
                FROM crawling AS cr
                LEFT JOIN maps AS cr_map
                    ON cr_map.map_id = cr.map_id
                WHERE cr.information_cd IS DISTINCT FROM '{RESTAURANT_INFORMATION_CD}'
                    AND NOT EXISTS (
                        SELECT 1
                        FROM analysis AS a
                        WHERE a.crawling_id = cr.crawling_id
                    )
            ),
            analysis_source AS (
                SELECT * FROM normalized_analysis
                UNION ALL
                SELECT * FROM crawling_only
            ),
            usable_analysis AS (
                -- content·keywords는 소스 CTE에서 이미 NULLIF(BTRIM(...), '') 처리됨.
                -- 빈 문자열은 NULL로 변환된 상태이므로 IS NOT NULL 체크만으로 충분하다.
                SELECT *
                FROM analysis_source
                WHERE crawling_id IS NOT NULL
                    AND information_cd IS NOT NULL
                    AND content IS NOT NULL
                    AND keywords IS NOT NULL
                    AND (
                        information_cd != '{RESTAURANT_INFORMATION_CD}'
                        OR sentimental IN ('positive', 'negative')
                    )
            ),
            last_post AS (
                SELECT shop_id, MAX(created_at) AS last_post_created_at
                FROM posts
                WHERE shop_id IS NOT NULL
                GROUP BY shop_id
            ),
            ic01_candidate AS (
                -- NOT EXISTS를 HAVING으로 이동: GROUP BY 이전 WHERE에 두면 같은 shop_id를 가진
                -- 행마다 correlated subquery가 실행된다. HAVING으로 올리면 그룹당 1회로 줄어든다.
                SELECT a.shop_id
                FROM usable_analysis AS a
                LEFT JOIN last_post AS p ON p.shop_id = a.shop_id
                WHERE a.information_cd = '{RESTAURANT_INFORMATION_CD}'
                    AND a.shop_id IS NOT NULL
                    AND (
                        p.last_post_created_at IS NULL
                        OR a.crawling_created_at > p.last_post_created_at
                    )
                GROUP BY a.shop_id
                HAVING COUNT(*) >= %s
                    AND NOT EXISTS (
                        SELECT 1
                        FROM posts
                        WHERE shop_id = a.shop_id
                        AND created_at::date = CURRENT_DATE
                    )
                    AND (
                        MAX(p.last_post_created_at) IS NULL
                        OR MAX(p.last_post_created_at) < NOW() - (%s * INTERVAL '1 day')
                    )
            )

            SELECT a.*
            FROM usable_analysis AS a
            INNER JOIN ic01_candidate AS c ON c.shop_id = a.shop_id
            LEFT JOIN last_post AS p ON p.shop_id = a.shop_id
            WHERE a.information_cd = '{RESTAURANT_INFORMATION_CD}'
                AND (
                    p.last_post_created_at IS NULL
                    OR a.crawling_created_at > p.last_post_created_at
                )

            UNION ALL

            SELECT a.*
            FROM usable_analysis AS a
            WHERE a.information_cd != '{RESTAURANT_INFORMATION_CD}'
                AND a.crawling_id IS NOT NULL
                AND NOT EXISTS (
                    SELECT 1
                    FROM posts
                    WHERE crawling_id = a.crawling_id
                )

            -- 마지막으로 처리된 row 바로 다음(오래된 것)부터 최신 순으로 처리하기 위해 ASC.
            -- crawling_created_at을 crawling_id 앞에 두어야 날짜 정렬이 실제로 적용된다.
            -- (crawling_id가 같으면 crawling_created_at은 상수값이므로 뒤에 두면 정렬 효과 없음)
            ORDER BY information_cd, shop_id NULLS LAST, crawling_created_at ASC, crawling_id
        """
        params = (min_rows, delay_days)

        cursor = get_cursor(query, params)

        if cursor is None:
            return  # 그냥 빈 generator로 종료

        yield from cursor  # fetchall() 없이 cursor 직접 순회

    except Exception as e:
        logger.error(f"get_data | Error={e} | time={time.time()}")
        raise  # 호출부로 예외 전파


def get_image(data: list[dict]) -> list:
    """
    게시글 생성 단위는 shop_id 기준이어도 이미지는 crawling_id 기준으로 저장된다.
    생성 묶음에 포함된 모든 crawling_id로 images에서 이미지 URL을 조회한다.
    이미 post_vector 컬렉션에 사용된 image_url은 제외한다.
    """
    try:
        if not data:
            return []

        crawling_ids = sorted({
            row.get("crawling_id")
            for row in data
            if row.get("crawling_id") is not None
        })

        if not crawling_ids:
            return []

        query = """
            SELECT i.image_url
            FROM images AS i
            WHERE i.table_cd = %s
                AND i.table_id = ANY(%s)
                AND NOT EXISTS (
                    SELECT 1
                    FROM langchain_pg_embedding AS e
                    INNER JOIN langchain_pg_collection AS c
                        ON c.uuid = e.collection_id
                    WHERE c.name = 'post_vector'
                    AND (
                        e.document LIKE '%%' || i.image_url || '%%'
                        OR e.cmetadata ->> 'image_url' = i.image_url
                    )
                )
        """

        cursor = get_cursor(query, (CRAWLING_IMAGE_TABLE_CD, crawling_ids))

        if not cursor:
            return []

        return cursor.fetchall()

    except Exception as e:
        logger.error(f"get_image | Error={e} | time={time.time()}")
        return []
