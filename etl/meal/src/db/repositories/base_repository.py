from typing import List, Dict, Any, Optional
from ...core.db_client import DBClient

class BaseRepository:
    """
    모든 Repository의 기본 클래스입니다.
    DBClient를 주입받아 기본적인 실행 인터페이스를 제공합니다.
    """
    
    def __init__(self, db_client: DBClient):
        self.db = db_client

    def execute(self, query: str, params: Optional[tuple] = None):
        return self.db.execute_query(query, params)

    def transaction(self, callback_fn):
        return self.db.execute_transaction(callback_fn)
