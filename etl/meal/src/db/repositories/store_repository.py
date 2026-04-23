from .base_repository import BaseRepository
from ..queries.store_queries import StoreQueries
from ...core.utils.decorators import db_transaction
from ...core.constants.pipeline_constants import CrawlerThread, PlatformSource

class StoreRepository(BaseRepository):
    """
    매장 및 관련 정보(메뉴, 리뷰, 이미지)의 DB 적재를 담당합니다.
    (6자 길이 제한 대응 버전)
    """

    def exists_by_url(self, source_url: str) -> bool:
        return False

    def exists_by_name_address(self, name: str, address: str) -> bool:
        res = self.execute(StoreQueries.SELECT_MAP_BY_NAME_ADDR, (name, address))
        return len(res) > 0

    @db_transaction
    def save_store(self, conn, cur, store_data: dict) -> int:
        """
        한 번의 트랜잭션으로 모든 테이블에 데이터를 적재합니다.
        """
        # 6자 이내로 코드값 조정 (Character Varying(6) 대응)
        category_cd = (store_data.get('category_cd') or 'SC06')[:6]
        address_cd = (store_data.get('address_cd') or '11000')[:6]
        shop_cd = PlatformSource.DININGCODE.value # DININGCODE(10자) 대신 5자 사용

        # 1. Maps 테이블 적재
        cur.execute(StoreQueries.INSERT_MAPS, (
            store_data.get('name'), 
            category_cd, 
            address_cd, 
            store_data.get('address_detail', ''),
            store_data.get('latitude'),
            store_data.get('longitude')
        ))
        map_id = cur.fetchone()[0]

        # 2. Shop 테이블 적재
        cur.execute(StoreQueries.INSERT_SHOP, (
            map_id,
            shop_cd,
            store_data.get('rating', 0.0)
        ))
        shop_id = cur.fetchone()[0]

        # 3. Menu 테이블 적재
        menus = store_data.get('menus', [])
        for menu in menus:
            cur.execute(StoreQueries.INSERT_MENU, (
                shop_id,
                menu.get('name'),
                menu.get('price')
            ))

        # 4. Crawling (Review) 테이블 적재
        reviews = store_data.get('reviews', [])
        for rev in reviews:
            cur.execute(StoreQueries.INSERT_CRAWLING, (
                map_id,
                rev.get('title', '리뷰'),
                rev.get('content', ''),
                CrawlerThread.REVIEW.value,
                '', 
                rev.get('point', 0.0),
                rev.get('author', 'anonymous'),
                category_cd
            ))
            crawling_id = cur.fetchone()[0]
            
            rev_images = rev.get('images', [])
            for img_url in rev_images:
                cur.execute(StoreQueries.INSERT_IMAGE, (img_url, 'crawling', crawling_id))

        # 5. 매장 대표 이미지 적재
        main_images = store_data.get('images', [])
        for img_url in main_images:
            cur.execute(StoreQueries.INSERT_IMAGE, (img_url, 'maps', map_id))
        
        return shop_id
