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
        """환경변수 URI로 DB에 접속해 ``autocommit`` 연결을 연다.

        Args:
            DB_CONFIG: 예약. 향후 설정 인젝션용.

        Note:
            함수 유형: D — 저장/조회 (연결)
            안전성: Level 2 — 운영 DB 연결 수립 (쓰기 쿼리 가능 상태)
            부작용: ``psycopg`` TCP 연결, 프로세스당 Singleton 1개
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
        """연결된 ``psycopg`` 커넥션 객체를 반환한다.

        Note:
            함수 유형: D — 저장/조회
            안전성: Level 1 — 연결 객체 반환만, 쿼리 실행 없음
        """
        return self.conn

    def run_query(self, query: str, **params):
        """명명 파라미터(``%(name)s``) SQL을 실행하고 ``fetchall`` 결과를 반환한다.

        Args:
            query: 실행할 SQL.
            **params: ``cursor.execute``에 전달할 명명 인자.

        Returns:
            조회 결과 행 목록.

        Note:
            함수 유형: D — 저장/조회
            안전성: Level 1~2 — 쿼리 내용에 따라 읽기(1) 또는 쓰기(2)
        """
        with self.conn.cursor() as cursor:
            cursor.execute(query, params)
            return cursor.fetchall()

    def run_query_lst(self, query: str, args: tuple | list | None = None) -> list:
        """위치 파라미터(``%s``) SQL을 실행하고 ``fetchall`` 결과를 반환한다.

        ``%(name)s``가 아닌 ``WHERE x = ANY(%s)`` 형태 등에 사용한다.

        Args:
            query: 실행할 SQL.
            args: 위치 인자 튜플·리스트.

        Returns:
            조회 결과 행 목록.

        Note:
            함수 유형: D — 저장/조회
            안전성: Level 1~2 — 쿼리 내용에 따라 달라짐
        """
        with self.conn.cursor() as cursor:
            cursor.execute(query, args or ())
            return cursor.fetchall()

    def test_conn(self) -> str:
        """``SELECT 1``로 연결 가능 여부를 확인하고 결과 메시지를 반환한다.

        Returns:
            성공 시 ``PostAnalysisErrors.Db.connection_successful()``,
            실패 시 예외 내용이 포함된 실패 메시지.

        Note:
            함수 유형: D — 저장/조회
            안전성: Level 1 — 읽기 전용 검증 쿼리
        """
        try:
            self.run_query("SELECT 1")
            return PostAnalysisErrors.Db.connection_successful()
        except Exception as e:
            return PostAnalysisErrors.Db.connection_failed(e)
