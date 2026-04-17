import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Dict, Any, List, Optional
from contextlib import contextmanager
from .file_manager import logger

class DBClient:
    """
    PostgreSQL 데이터베이스 연결 및 쿼리 실행을 관리합니다.
    """
    
    def __init__(self, conn_params: Dict[str, Any]):
        self.conn_params = conn_params

    @contextmanager
    def get_connection(self):
        """커넥션 컨텍스트 매니저 (자동 close)"""
        conn = psycopg2.connect(**self.conn_params)
        try:
            yield conn
        finally:
            conn.close()

    @contextmanager
    def get_cursor(self, conn):
        """커서 컨텍스트 매니저 (자동 close)"""
        cur = conn.cursor()
        try:
            yield cur
        finally:
            cur.close()

    def execute_query(self, query: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        """단순 SELECT 쿼리 실행용"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query, params)
                return cur.fetchall()

    def execute_transaction(self, callback_fn):
        """
        복잡한 트랜잭션 로직을 실행합니다. 
        callback_fn은 conn과 cur을 인자로 받아 로직을 수행해야 합니다.
        """
        with self.get_connection() as conn:
            try:
                with conn.cursor() as cur:
                    result = callback_fn(conn, cur)
                    conn.commit()
                    return result
            except Exception as e:
                conn.rollback()
                logger.error(f"!!! Database Transaction Error: {str(e)}")
                raise e
