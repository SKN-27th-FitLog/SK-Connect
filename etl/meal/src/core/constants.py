"""
SQL 쿼리 상수 관리 모듈.
설계안 8.1 및 22.5 준수: SQL은 반드시 상수화하며 코드 테이블 값 하드코딩 금지.
기존 init.sql 스키마와 100% 동기화.
"""

# ---------------------------------------------------------
# 1. Code Table Queries (설계안 7장 관련)
# ---------------------------------------------------------

QUERY_SELECT_ALL_CODES = 'SELECT cd, name, cd_info, cd_upper FROM "codeT"'
QUERY_SELECT_ALL_ADDRESS_CODES = 'SELECT cd as address_cd, name FROM "codeT" WHERE cd_upper = \'LA00\''
QUERY_SELECT_ALL_SHOP_CODES = 'SELECT cd as code, name FROM "codeT" WHERE cd_upper = \'SC00\''
QUERY_SELECT_PROCESSED_URLS = 'SELECT article_url FROM crawling WHERE article_url IS NOT NULL'
RESTAURANT_CATEGORY_CD = "CA01"
SHOP_CODE_PREFIX = "SC"

# ---------------------------------------------------------
# 2. Store / Data Queries (설계안 17, 20장 - 정규화 적재)
# ---------------------------------------------------------

# 2.1 Maps save queries
QUERY_FIND_MAP = """
    SELECT map_id
    FROM maps
    WHERE name = :name
      AND category_cd = :category_cd
      AND address_cd = :address_cd
      AND address_detail = :address_detail
    LIMIT 1
"""

QUERY_INSERT_MAP = """
    INSERT INTO maps (name, category_cd, address_cd, address_detail, latitude, longitude)
    VALUES (:name, :category_cd, :address_cd, :address_detail, :latitude, :longitude)
    RETURNING map_id
"""

QUERY_UPDATE_MAP_COORDINATES = """
    UPDATE maps
    SET latitude = :latitude,
        longitude = :longitude
    WHERE map_id = :map_id
"""

# 2.2 Shop save queries
QUERY_FIND_SHOP = """
    SELECT shop_id
    FROM shop
    WHERE map_id = :map_id
      AND shop_cd = :shop_cd
    LIMIT 1
"""

QUERY_INSERT_SHOP = """
    INSERT INTO shop (map_id, shop_cd, rating)
    VALUES (:map_id, :shop_cd, :rating)
    RETURNING shop_id
"""

QUERY_UPDATE_SHOP_RATING = """
    UPDATE shop
    SET rating = :rating
    WHERE shop_id = :shop_id
"""

QUERY_TOUCH_SHOP_CHECKED_AT = """
    INSERT INTO crawling (title, content, article_url, map_id, category_cd, author, keywords, point, created_at)
    SELECT
        :title,
        :content,
        :article_url,
        s.map_id,
        COALESCE(:category_cd, m.category_cd),
        :author,
        :keywords,
        :point,
        NOW()
    FROM shop s
    JOIN maps m ON m.map_id = s.map_id
    WHERE s.shop_id = :shop_id
    RETURNING crawling_id
"""

# 2.3 Crawling Insert (확장됨)
QUERY_INSERT_CRAWLING = """
    INSERT INTO crawling (title, content, article_url, map_id, category_cd, author, keywords, point, created_at)
    SELECT
        CAST(:title AS VARCHAR(200)),
        :content,
        CAST(:article_url AS VARCHAR(500)),
        :map_id,
        CAST(:category_cd AS VARCHAR(6)),
        CAST(:author AS VARCHAR(100)),
        CAST(:keywords AS VARCHAR(100)),
        :point,
        NOW()
    WHERE NOT EXISTS (
        SELECT 1
        FROM crawling
        WHERE article_url = CAST(:article_url AS VARCHAR(500))
          AND map_id = :map_id
          AND title = CAST(:title AS VARCHAR(200))
          AND content = :content
          AND author = CAST(:author AS VARCHAR(100))
    )
    RETURNING crawling_id
"""

# 2.4 Menu Insert
QUERY_INSERT_MENU = """
    INSERT INTO menu (shop_id, name, price)
    SELECT :shop_id, CAST(:name AS VARCHAR(100)), :price
    WHERE NOT EXISTS (
        SELECT 1
        FROM menu
        WHERE shop_id = :shop_id
          AND name = CAST(:name AS VARCHAR(100))
    )
"""

# 2.5 Images Insert
QUERY_INSERT_IMAGE = """
    INSERT INTO images (image_url, table_name, table_id)
    SELECT CAST(:image_url AS VARCHAR(500)), CAST(:table_name AS VARCHAR(20)), :table_id
    WHERE NOT EXISTS (
        SELECT 1
        FROM images
        WHERE image_url = CAST(:image_url AS VARCHAR(500))
          AND table_name = CAST(:table_name AS VARCHAR(20))
          AND table_id = :table_id
    )
"""

# ---------------------------------------------------------
# 3. Operational Constants
# ---------------------------------------------------------

PROCESS_RAW = "raw"
PROCESS_CANDIDATE = "candidate"
PROCESS_NORMALIZED = "normalized"
PROCESS_FAIL_LEDGER = "fail_ledger"

SERVICE_SHOP = "shop"
SERVICE_MENU = "menu"
SERVICE_REVIEW = "review"

STATUS_SUCCESS = "success"
STATUS_FAIL = "fail"


# ---------------------------------------------------------
# 4. store repository queries
# ---------------------------------------------------------

# 4.1 find success loaded dedup keys
QUERY_FIND_SUCCESS_LOADED_DEDUP_KEYS = """
    SELECT m.name, m.address_cd
    FROM maps m
    JOIN shop s ON s.map_id = m.map_id
    WHERE m.category_cd = :category_cd
      AND s.shop_cd = :shop_cd
"""

# 4.2 find update targets
QUERY_FIND_UPDATE_TARGETS = """
            SELECT
                s.shop_id AS store_id,
                m.map_id,
                m.address_cd,
                m.category_cd,
                MAX(c.created_at) AS last_checked_at,
                (ARRAY_AGG(c.article_url ORDER BY c.created_at DESC)
                    FILTER (WHERE c.article_url IS NOT NULL))[1] AS article_url
            FROM shop s
            JOIN maps m ON m.map_id = s.map_id
            LEFT JOIN crawling c ON c.map_id = m.map_id
            WHERE m.category_cd = :category_cd
              AND s.shop_cd = :shop_cd
            GROUP BY s.shop_id, m.map_id, m.address_cd, m.category_cd
            HAVING
                (ARRAY_AGG(c.article_url ORDER BY c.created_at DESC)
                    FILTER (WHERE c.article_url IS NOT NULL))[1] IS NOT NULL
                AND (
                    MAX(c.created_at) IS NULL
                    OR MAX(c.created_at) <= NOW() - (:refresh_interval_days * INTERVAL '1 day')
                )
            ORDER BY MAX(c.created_at) ASC NULLS FIRST
            LIMIT :limit
        """

# 4.3 bulk find snapshots
QUERY_BULK_FIND_SNAPSHOTS = """
            SELECT
                s.shop_id AS store_id,
                m.map_id,
                m.name,
                m.address_cd,
                NULL::TEXT AS store_content_hash,
                NULL::TEXT AS menu_content_hash,
                NULL::TEXT AS review_content_hash,
                NULL::TEXT AS image_content_hash,
                MAX(c.created_at) AS last_updated_at,
                MAX(c.created_at) AS last_checked_at,
                (ARRAY_AGG(c.article_url ORDER BY c.created_at DESC)
                    FILTER (WHERE c.article_url IS NOT NULL))[1] AS article_url
            FROM shop s
            JOIN maps m ON m.map_id = s.map_id
            LEFT JOIN crawling c ON c.map_id = m.map_id
            WHERE c.article_url = ANY(:dedup_keys)
               OR CONCAT(REPLACE(COALESCE(m.name, ''), ' ', ''), '|', m.address_cd) = ANY(:dedup_keys)
            GROUP BY s.shop_id, m.map_id, m.name, m.address_cd
        """

# 4.4 find snapshot by dedup key
QUERY_FIND_SNAPSHOT_BY_DEDUP_KEY = """
            SELECT
                s.shop_id AS store_id,
                m.map_id,
                NULL::TEXT AS store_content_hash,
                NULL::TEXT AS menu_content_hash,
                NULL::TEXT AS review_content_hash,
                NULL::TEXT AS image_content_hash,
                MAX(c.created_at) AS last_updated_at,
                MAX(c.created_at) AS last_checked_at,
                (ARRAY_AGG(c.article_url ORDER BY c.created_at DESC)
                    FILTER (WHERE c.article_url IS NOT NULL))[1] AS article_url
            FROM shop s
            JOIN maps m ON m.map_id = s.map_id
            LEFT JOIN crawling c ON c.map_id = m.map_id
            WHERE c.article_url = :dedup_key
               OR CONCAT(REPLACE(COALESCE(m.name, ''), ' ', ''), '|', m.address_cd) = :dedup_key
            GROUP BY s.shop_id, m.map_id
            LIMIT 1
        """

