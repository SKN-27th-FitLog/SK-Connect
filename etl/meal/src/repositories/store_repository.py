from .base_repository import BaseRepository
from ..queries.store_queries import INSERT_MAPS, INSERT_SHOP, SELECT_MAP_BY_URL, SELECT_MAP_BY_NAME_ADDR
from ..utils.decorators import db_transaction

class StoreRepository(BaseRepository):
    """
    매장(maps, shop) 관련 DB 접근을 담당하는 리포지토리입니다.
    """

    def exists_by_url(self, source_url: str) -> bool:
        """source_url로 매장 중복 여부를 확인합니다."""
        res = self.execute(SELECT_MAP_BY_URL, (source_url,))
        return len(res) > 0

    def exists_by_name_address(self, name: str, address: str) -> bool:
        """상호명과 상세주소로 매장 중복 여부를 확인합니다."""
        res = self.execute(SELECT_MAP_BY_NAME_ADDR, (name, address))
        return len(res) > 0

    @db_transaction
    def save_store(self, conn, cur, store_data: dict) -> int:
        """
        매장 정보를 트랜잭션 단위로 저장합니다. (maps + shop)
        @db_transaction 데코레이터가 conn, cur을 주입합니다.
        """
        # 1. Maps 저장
        cur.execute(INSERT_MAPS, (
            store_data['name'], 
            store_data['category_cd'], 
            store_data['address_cd'], 
            store_data['address_detail'], 
            store_data['latitude'], 
            store_data['longitude']
        ))
        map_id = cur.fetchone()[0]
        
        # 2. Shop 저장
        cur.execute(INSERT_SHOP, (
            map_id,
            store_data['shop_cd'],
            store_data.get('rating', 0.0)
        ))
        shop_id = cur.fetchone()[0]
        
        return shop_id
