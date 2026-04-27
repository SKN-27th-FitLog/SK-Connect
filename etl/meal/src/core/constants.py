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

# ---------------------------------------------------------
# 2. Store / Data Queries (설계안 17, 20장 - 정규화 적재)
# ---------------------------------------------------------

# 2.1 Maps Upsert
QUERY_UPSERT_MAP = """
    INSERT INTO maps (name, category_cd, address_cd, address_detail, latitude, longitude)
    VALUES (:name, :category_cd, :address_cd, :address_detail, :latitude, :longitude)
    ON CONFLICT (name, category_cd, address_cd, address_detail)
    DO UPDATE SET
        latitude = EXCLUDED.latitude,
        longitude = EXCLUDED.longitude
    RETURNING map_id
"""

# 2.2 Shop Upsert
QUERY_UPSERT_SHOP = """
    INSERT INTO shop (
        map_id, shop_cd, rating,
        store_content_hash, menu_content_hash, review_content_hash, image_content_hash,
        last_checked_at
    )
    VALUES (
        :map_id, :shop_cd, :rating,
        :store_content_hash, :menu_content_hash, :review_content_hash, :image_content_hash,
        NOW()
    )
    ON CONFLICT (map_id, shop_cd)
    DO UPDATE SET
        rating = EXCLUDED.rating,
        store_content_hash = EXCLUDED.store_content_hash,
        menu_content_hash = EXCLUDED.menu_content_hash,
        review_content_hash = EXCLUDED.review_content_hash,
        image_content_hash = EXCLUDED.image_content_hash,
        last_checked_at = NOW()
    RETURNING shop_id
"""

QUERY_TOUCH_SHOP_CHECKED_AT = """
    UPDATE shop
    SET last_checked_at = NOW()
    WHERE shop_id = :shop_id
"""

# 2.3 Crawling Insert (확장됨)
QUERY_INSERT_CRAWLING = """
    INSERT INTO crawling (title, content, article_url, map_id, category_cd, author, keywords, point, created_at)
    VALUES (:title, :content, :article_url, :map_id, :category_cd, :author, :keywords, :point, NOW())
    RETURNING crawling_id
"""

# 2.4 Menu Insert
QUERY_INSERT_MENU = """
    INSERT INTO menu (shop_id, name, price)
    VALUES (:shop_id, :name, :price)
"""

# 2.5 Images Insert
QUERY_INSERT_IMAGE = """
    INSERT INTO images (image_url, table_name, table_id)
    VALUES (:image_url, :table_name, :table_id)
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

find_success_loaded_dedup_keys = """
    SELECT name, address_cd
    FROM maps
    WHERE category_cd = :category_cd
"""

find_update_targets = """
            SELECT
                s.shop_id AS store_id,
                m.address_cd,
                m.category_cd,
                s.last_checked_at
            FROM shop s
            JOIN maps m ON m.map_id = s.map_id
            WHERE m.category_cd = :category_cd
              AND (
                    s.last_checked_at IS NULL
                    OR s.last_checked_at <= NOW() - (:refresh_interval_days * INTERVAL '1 day')
              )
            ORDER BY s.last_checked_at ASC NULLS FIRST
            LIMIT :limit
        """

find_snapshot_by_dedup_key="""
            SELECT
                s.shop_id AS store_id,
                m.map_id,
                s.store_content_hash,
                s.menu_content_hash,
                s.review_content_hash,
                s.image_content_hash,
                s.updated_at AS last_updated_at,
                s.last_checked_at
            FROM shop s
            JOIN maps m ON m.map_id = s.map_id
            WHERE s.dedup_key = :dedup_key OR m.canonical_url = :dedup_key
            LIMIT 1
        """

# ---------------------------------------------------------
# 5.fail repository queries
# ---------------------------------------------------------

get_retry_targets = """
            SELECT entity_id, entity_ref, reason_code, retry_count
            FROM fail_ledger
            WHERE category_cd = :category_cd 
              AND source_platform = :platform
              AND action = 'RETRY'
              AND retry_count < 5
        """
