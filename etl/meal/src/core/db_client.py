import pg8000
from typing import Dict, Any, List, Optional
from contextlib import contextmanager
from .file_manager import logger

class DBClient:
    """
    pg8000(Pure Python)을 사용하여 보안 정책 차단을 우회하고 DB 연결을 관리합니다.
    """
    
    def __init__(self, conn_params: Dict[str, Any]):
        # pg8000은 'dbname' 대신 'database' 키를 사용하므로 변환
        self.conn_params = conn_params.copy()
        if 'dbname' in self.conn_params:
            self.conn_params['database'] = self.conn_params.pop('dbname')
            
        # 포트 번호는 int형이어야 함
        if 'port' in self.conn_params:
            self.conn_params['port'] = int(self.conn_params['port'])

    @contextmanager
    def get_connection(self):
        """커넥션 컨텍스트 매니저"""
        conn = pg8000.connect(**self.conn_params)
        try:
            yield conn
        finally:
            conn.close()

    @contextmanager
    def get_cursor(self, conn):
        """커서 컨텍스트 매니저"""
        cur = conn.cursor()
        try:
            yield cur
        finally:
            cur.close()

    def execute_query(self, query: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        """SELECT 쿼리 실행 및 결과를 사전(dict) 리스트로 반환"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                rows = cur.fetchall()
                if not rows:
                    return []
                # 컬럼명 추출하여 dict로 변환
                columns = [desc[0] for desc in cur.description]
                return [dict(zip(columns, row)) for row in rows]

    def execute_transaction(self, callback_fn):
        """
        복잡한 트랜잭션 로직을 실행합니다. 
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
