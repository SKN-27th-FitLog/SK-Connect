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
    RETURNING map_id
"""

# 2.2 Shop Upsert
QUERY_UPSERT_SHOP = """
    INSERT INTO shop (map_id, shop_cd, rating)
    VALUES (:map_id, :shop_cd, :rating)
    RETURNING shop_id
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
