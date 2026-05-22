"""`python -m postgresql` — DB 연결·샘플 쿼리 테스트."""

from __future__ import annotations

import logging

from postgresql.config import SQL_SAMPLE_CRAWLING
from postgresql.connection import PostgreDB

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main() -> None:
    """DB 연결 스모크 및 `crawling` 샘플 조회 CLI.

    Note:
        함수 유형: F — 인프라 진입
        안전성: Level 1 — 읽기 위주
    """
    db = PostgreDB()
    logger.info(db.test_conn())
    result = db.run_query(SQL_SAMPLE_CRAWLING)
    logger.info("sample rows: %s", result)


if __name__ == "__main__":
    main()
