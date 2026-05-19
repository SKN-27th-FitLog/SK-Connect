"""`python -m postgresql` — DB 연결·샘플 쿼리 테스트."""

from __future__ import annotations

import logging

from postgresql.config import SQL_SAMPLE_CRAWLING
from postgresql.connection import PostgreDB

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main() -> None:
    db = PostgreDB()
    logger.info(db.test_conn())
    result = db.run_query(SQL_SAMPLE_CRAWLING)
    logger.info("sample rows: %s", result)


if __name__ == "__main__":
    main()
