"""PostgreSQL 연결(Singleton) 및 간단 쿼리 헬퍼."""

# 패키지
import os

import psycopg

# 모듈
import common.env  # noqa: F401 — `.env` 로드
from common.errors import PostAnalysisErrors
from common.singleton import Singleton
from postgresql.config import PostgresEnvKey


##############################
# conn 설정
##############################
class PostgreDB(metaclass=Singleton):
    """`.env`의 ``PG*`` 변수로 `psycopg` 연결을 맺는다 (프로세스당 단일 커넥션)."""

    def __init__(self, DB_CONFIG: dict | None = None):
        """환경변수 URI로 DB에 접속해 `autocommit` 연결을 연다.

        Args:
            DB_CONFIG: 예약. 향후 설정 인젝션용.
        """

        user = os.getenv(PostgresEnvKey.USER.value)
        password = os.getenv(PostgresEnvKey.PASSWORD.value)
        host = os.getenv(PostgresEnvKey.HOST.value)
        port = os.getenv(PostgresEnvKey.PORT.value)
        database = os.getenv(PostgresEnvKey.DATABASE.value)

        # PostgreSQL 연결 설정
        db_uri = f"postgresql://{user}:{password}@{host}:{port}/{database}"
        self.conn = psycopg.connect(db_uri, autocommit=True)

    def get_conn(self):
        """연결된 커넥션 객체를 반환 (연결 확인용)."""
        return self.conn

    def run_query(self, query: str, **params):
        """
        전달받은 쿼리랑 인자를 실행하고 결과를 반환하는 함수.
        들어가는 인자들은 인자 이름을 같이 넣어줘야 사용 가능함.
        """
        with self.conn.cursor() as cursor:
            cursor.execute(query, params)
            return cursor.fetchall()

    def run_query_lst(self, query: str, args: tuple | list | None = None) -> list:
        """
        인자가 아니라 위치 기준으로 반복되는 데이터를 여러개 넣게 되서 만든 별도 함수.
        `%(name)s`가 아닌 `%s` 자리(튜플·리스트)용. 예: `WHERE x = ANY(%s)`.
        """
        with self.conn.cursor() as cursor:
            cursor.execute(query, args or ())
            return cursor.fetchall()

    def test_conn(self) -> str:
        """연결 확인용 쿼리 실행."""
        try:
            self.run_query("SELECT 1")
            return PostAnalysisErrors.Db.connection_successful()
        except Exception as e:
            return PostAnalysisErrors.Db.connection_failed(e)
