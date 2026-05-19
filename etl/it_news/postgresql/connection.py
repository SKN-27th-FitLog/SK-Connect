"""PostgreSQL 연결 싱글톤."""

from __future__ import annotations

import logging

import psycopg

from common.errors import EtlErrors
from postgresql.config import SQL_TEST_CONNECTION, build_dsn
from postgresql.singleton import Singleton

logger = logging.getLogger(__name__)


class PostgreDB(metaclass=Singleton):
    def __init__(self) -> None:
        self.conn = psycopg.connect(build_dsn(), autocommit=True)

    def get_conn(self):
        """연결된 커넥션 객체를 반환 (연결 확인용)."""
        return self.conn

    def run_query(self, query: str, **params):
        """이름 기반 파라미터(`%(name)s`) 쿼리 실행."""
        with self.conn.cursor() as cursor:
            cursor.execute(query, params)
            return cursor.fetchall()

    def run_query_lst(self, query: str, args: tuple | list | None = None) -> list:
        """위치 기반 파라미터(`%s`) 쿼리 실행."""
        with self.conn.cursor() as cursor:
            cursor.execute(query, args or ())
            return cursor.fetchall()

    def test_conn(self) -> str:
        """연결 확인용 쿼리 실행."""
        try:
            self.run_query(SQL_TEST_CONNECTION)
            return "Connection successful"
        except Exception as e:
            return EtlErrors.Db.connection_failed(str(e))
