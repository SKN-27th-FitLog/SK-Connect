"""
매장(maps, shop) 관련 SQL 상수를 정의합니다.
"""

# Maps 테이블 UPSERT (v4 Deduplication 기준 반영을 위한 준비)
INSERT_MAPS = """
INSERT INTO maps (name, category_cd, address_cd, address_detail, latitude, longitude)
VALUES (%s, %s, %s, %s, %s, %s)
RETURNING map_id
"""

# Shop 테이블 INSERT
INSERT_SHOP = """
INSERT INTO shop (map_id, shop_cd, rating)
VALUES (%s, %s, %s)
RETURNING shop_id
"""

# 중복 체크 쿼리 (SyncService용)
SELECT_MAP_BY_URL = "SELECT map_id FROM maps WHERE source_url = %s"
SELECT_MAP_BY_NAME_ADDR = "SELECT map_id FROM maps WHERE name = %s AND address_detail = %s"

# --- Stage 0: Target Selection 전용 쿼리 ---

# 1. 특정 카테고리의 성공 적재된 가게 URL 목록 조회
SELECT_LOADED_STORE_URLS = "SELECT source_url as canonical_url FROM maps WHERE category_cd = %s"

# 2. 실패 내역(Fail Ledger)에서 재시도 대상(action='retry') 조회
SELECT_RETRY_TARGETS = """
    SELECT entity_id as canonical_url, retry_count 
    FROM fail_ledger 
    WHERE category_cd = %s AND action = 'retry' AND status = 'fail'
"""

# 3. 소스 풀(Source Pool)에서 신규 후보 추출 (기존 적재되지 않은 건)
SELECT_NEW_CANDIDATES = """
    SELECT source_url as canonical_url 
    FROM store_source_pool 
    WHERE category_cd = %s 
      AND source_url NOT IN (SELECT source_url FROM maps)
    ORDER BY created_at ASC
    LIMIT %s
"""

