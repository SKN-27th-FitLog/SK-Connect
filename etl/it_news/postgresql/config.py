"""PostgreSQL 연결·스키마 상수. 연결 정보는 `etl/it_news/.env`에서 읽는다."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

from common.errors import EtlErrors

_ENV_FILE = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_ENV_FILE)


class PgEnv:
    """`.env` 환경변수 키 이름 (연결 전용)."""

    USER = "PGUSER"
    PASSWORD = "PGPASSWORD"
    HOST = "PGHOST"
    PORT = "PGPORT"
    DATABASE = "PGDATABASE"


def require_env(key: str) -> str:
    """`.env`에서 필수 연결 값을 읽는다. 없거나 비어 있으면 `ValueError`."""
    value = os.getenv(key)
    if value is None or not str(value).strip():
        raise ValueError(EtlErrors.Db.missing_env_var(key))
    return str(value).strip()


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
    """`.env`의 연결 변수로 PostgreSQL URI를 만든다."""
    user = require_env(PgEnv.USER)
    password = require_env(PgEnv.PASSWORD)
    host = require_env(PgEnv.HOST)
    port = require_env(PgEnv.PORT)
    database = require_env(PgEnv.DATABASE)
    return f"postgresql://{user}:{password}@{host}:{port}/{database}"
