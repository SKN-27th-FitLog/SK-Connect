# 패키지
from dotenv import load_dotenv
import psycopg
import os
import logging

# 모듈
from common.singleton import Singleton

load_dotenv()


##############################
# conn 설정
##############################
class PostgreDB(metaclass=Singleton):
    def __init__(self, DB_CONFIG:dict=None):

        user = os.getenv('PGUSER')
        password = os.getenv('PGPASSWORD')
        host = os.getenv('PGHOST')
        port = os.getenv('PGPORT')
        database = os.getenv('PGDATABASE')

        # PostgreSQL 연결 설정
        DB_URI = f"postgresql://{user}:{password}@{host}:{port}/{database}"

        self.conn = psycopg.connect(DB_URI, autocommit=True)

    def get_conn(self):
        """ 연결된 커넥션 객체를 반환 (연결 확인용 )"""
        return self.conn

    def run_query(self, query:str, **params):
        """ 전달받은 쿼리랑 인자를 실행하고 결과를 반환하는 함수 """
        with self.conn.cursor() as cursor:
            cursor.execute(query, params)
            return cursor.fetchall()

    def test_conn(self)-> str:
        """ 연결 확인용 쿼리 실행 """
        try:
            self.run_query("SELECT 1")
            return "Connection successful"
        except Exception as e:
            return f"Connection failed: {e}"



if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    # 커넥션 설정
    db = PostgreDB()

    # 연결 테스트 
    logger.info(db.test_conn())

    # 쿼리 테스트 
    query = "SELECT * FROM crawling LIMIT 5;"
    result = db.run_query(query)
    logger.info(result)