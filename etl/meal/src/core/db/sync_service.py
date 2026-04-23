from typing import Dict, Any, List, Optional, Tuple
from ..db_client import DBClient
from ..constants.schema_constants import MapsColumns

class DBSyncService:
    """
    데이터베이스 적재 전 중복 체크 및 동기화 무결성을 보장합니다.
    (v4.0: Hierarchical Deduplication - source_url -> name+address)
    """
    
    def __init__(self, db_client: DBClient):
        self.db = db_client

    def exists_in_db(self, table_name: str, data: Dict[str, Any]) -> Tuple[bool, Optional[int]]:
        """
        중복 판별 우선순위에 따라 데이터 존재 여부를 확인합니다.
        1순위: source_url (Maps 테이블 기준)
        2순위: name + address_detail (AND 조건)
        """
        if table_name not in ["maps", "shop"]:
             # crawling 등은 중복 적재 허용하거나 별도 처리가 필요할 수 있으나 현재는 통과
            return False, None

        # 1순위: source_url 체크
        source_url = data.get(MapsColumns.SOURCE_URL.value)
        if source_url:
            query = "SELECT map_id FROM maps WHERE source_url = %s"
            res = self.db.execute_query(query, (source_url,))
            if res:
                return True, res[0]["map_id"]

        # 2순위: name + address_detail 체크
        name = data.get(MapsColumns.NAME.value)
        address = data.get(MapsColumns.ADDRESS_DETAIL.value)
        if name and address:
            query = "SELECT map_id FROM maps WHERE name = %s AND address_detail = %s"
            res = self.db.execute_query(query, (name, address))
            if res:
                return True, res[0]["map_id"]

        return False, None
    
    def check_article_exists(self, thread: str, article_url: str) -> bool:
        """crawling 테이블 전용 중복 체크 (article_url 기준)"""
        query = "SELECT crawling_id FROM crawling WHERE thread = %s AND article_url = %s"
        res = self.db.execute_query(query, (thread, article_url))
        return len(res) > 0
