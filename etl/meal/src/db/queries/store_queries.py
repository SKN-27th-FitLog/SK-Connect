"""
매장(maps, shop, menu, crawling, images) 관련 SQL 상수를 정의합니다.
(source_url 컬럼 부재로 인해 해당 참조를 모두 제거한 버전)
"""

class StoreQueries:
    # 1. Maps 테이블 (식당 기본 정보)
    INSERT_MAPS = """
        INSERT INTO maps (name, category_cd, address_cd, address_detail, latitude, longitude)
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING map_id
    """
    
    # 2. Shop 테이블 (서비스별 상세 정보)
    INSERT_SHOP = """
        INSERT INTO shop (map_id, shop_cd, rating)
        VALUES (%s, %s, %s)
        RETURNING shop_id
    """
    
    # 3. Menu 테이블
    INSERT_MENU = """
        INSERT INTO menu (shop_id, name, price)
        VALUES (%s, %s, %s)
    """
    
    # 4. Crawling 테이블 (리뷰 데이터)
    INSERT_CRAWLING = """
        INSERT INTO crawling (map_id, title, content, thread, article_url, point, author, category_cd)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING crawling_id
    """
    
    # 5. Images 테이블
    INSERT_IMAGE = """
        INSERT INTO images (image_url, table_name, table_id)
        VALUES (%s, %s, %s)
    """
    
    # 중복 체크 쿼리 (source_url 제외)
    SELECT_MAP_BY_NAME_ADDR = "SELECT map_id FROM maps WHERE name = %s AND address_detail = %s"

    # [Stage 0] 대상 확인용 - source_url 부재로 인해 상호명 목록으로 대체하거나 빈 쿼리 처리
    # 일단 에러 방지를 위해 name을 canonical_url로 별칭 주어 반환 (구조 유지용)
    SELECT_LOADED_STORE_NAMES = "SELECT name as canonical_url FROM maps WHERE category_cd = %s"
