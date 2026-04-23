"""
매장(maps, shop) 관련 SQL 상수를 정의합니다.
"""

class StoreQueries:
    # Maps 테이블 (식당 기본 정보)
    INSERT_MAPS = """
        INSERT INTO maps (name, category_cd, address_cd, address_detail, latitude, longitude, source_url)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        RETURNING map_id
    """
    
    # Shop 테이블 (서비스별 상세 정보)
    INSERT_SHOP = """
        INSERT INTO shop (map_id, shop_cd, rating)
        VALUES (%s, %s, %s)
        RETURNING shop_id
    """
    
    # 중복 체크 쿼리 (SyncService용)
    SELECT_MAP_BY_URL = "SELECT map_id FROM maps WHERE source_url = %s"
    SELECT_MAP_BY_NAME_ADDR = "SELECT map_id FROM maps WHERE name = %s AND address_detail = %s"

    # [Stage 0] 대상 확인용
    SELECT_LOADED_STORE_URLS = "SELECT source_url as canonical_url FROM maps WHERE category_cd = %s"

