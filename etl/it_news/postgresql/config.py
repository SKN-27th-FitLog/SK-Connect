"""PostgreSQL 연결·스키마 상수. 이 패키지만 분리해도 DB 레이어가 동작하도록 구성."""

from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()


class PgEnv:
    """`.env` 환경변수 키."""

    USER = "PGUSER"
    PASSWORD = "PGPASSWORD"
    HOST = "PGHOST"
    PORT = "PGPORT"
    DATABASE = "PGDATABASE"


class PgDefaults:
    PORT = "5432"


TABLE_CRAWLING = "crawling"
COL_CREATED_AT = "created_at"
COL_THREAD = "thread"

SQL_MAX_CREATED_AT_ALL = f"SELECT MAX({COL_CREATED_AT}) FROM {TABLE_CRAWLING}"
SQL_MAX_CREATED_AT_BY_THREAD_PREFIX = (
    f"SELECT MAX({COL_CREATED_AT}) FROM {TABLE_CRAWLING} WHERE {COL_THREAD} ~ %s"
)
SQL_TEST_CONNECTION = "SELECT 1"
SQL_SAMPLE_CRAWLING = f"SELECT * FROM {TABLE_CRAWLING} LIMIT 5;"


def build_dsn() -> str:
    """환경변수로 PostgreSQL URI를 만든다."""
    user = os.getenv(PgEnv.USER)
    password = os.getenv(PgEnv.PASSWORD)
    host = os.getenv(PgEnv.HOST)
    port = os.getenv(PgEnv.PORT, PgDefaults.PORT)
    database = os.getenv(PgEnv.DATABASE)
    return f"postgresql://{user}:{password}@{host}:{port}/{database}"
