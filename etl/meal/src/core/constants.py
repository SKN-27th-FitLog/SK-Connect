"""
SQL 쿼리 상수 관리 모듈.
설계안 8.1 및 22.5 준수: SQL은 반드시 상수화하며 코드 테이블 값 하드코딩 금지.
"""

# ---------------------------------------------------------
# 1. Code Table Queries (설계안 7장 관련)
# ---------------------------------------------------------

# 전체 코드 테이블 조회 (캐싱용)
# 주소(maps), 카테고리(codeT 등) 테이블 구조에 따라 필드명 조정 필요
QUERY_SELECT_ALL_ADDRESS_CODES = """
    SELECT address_cd, province, city, district 
    FROM maps
"""

QUERY_SELECT_ALL_SHOP_CODES = """
    SELECT code, name 
    FROM shop_codes
"""

QUERY_SELECT_SUCCESSFUL_STORE_IDS = """
    SELECT source_internal_id 
    FROM shop 
    WHERE source_platform = :platform
"""

QUERY_SELECT_RETRY_TARGETS = """
    SELECT target_id, url, category_cd, retry_count
    FROM targets
    WHERE status = 'RETRY' AND retry_count < :max_retries
"""

QUERY_SELECT_NEW_TARGETS = """
    SELECT target_id, url, category_cd
    FROM targets
    WHERE status = 'PENDING'
    LIMIT :limit
"""


# ---------------------------------------------------------
# 2. Store / Data Queries (설계안 17, 20장 관련)
# ---------------------------------------------------------

QUERY_UPSERT_STORE = """
    INSERT INTO shop (
        store_id, shop_cd, name, address_cd, address_detail, 
        latitude, longitude, canonical_url, source_platform, 
        source_internal_id, dedup_key, dedup_key_type, updated_at
    ) 
    VALUES (
        :store_id, :shop_cd, :name, :address_cd, :address_detail, 
        :latitude, :longitude, :canonical_url, :source_platform, 
        :source_internal_id, :dedup_key, :dedup_key_type, NOW()
    )
    ON CONFLICT (dedup_key) DO UPDATE SET
        name = EXCLUDED.name,
        address_detail = EXCLUDED.address_detail,
        latitude = EXCLUDED.latitude,
        longitude = EXCLUDED.longitude,
        updated_at = NOW()
"""


# ---------------------------------------------------------
# 3. Fail Ledger Queries (설계안 14장 관련)
# ---------------------------------------------------------

QUERY_INSERT_FAIL_LEDGER = """
    INSERT INTO fail_ledger (
        batch_id, stage, entity_type, entity_id, 
        reason_code, action, detail, retry_count, created_at
    )
    VALUES (
        :batch_id, :stage, :entity_type, :entity_id, 
        :reason_code, :action, :detail, :retry_count, NOW()
    )
"""
