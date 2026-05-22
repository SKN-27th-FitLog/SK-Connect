"""DB 연결·샘플 쿼리 검증: ``python -m postgresql``."""

import logging

from postgresql.config import PostgreSqlTable
from postgresql.connection import PostgreDB


def main() -> None:
    """DB 연결 및 ``crawling`` 샘플 조회로 로컬 환경을 검증한다.

    ``python -m postgresql`` 진입점.

    Note:
        함수 유형: F — 오케스트레이션 (진단)
        안전성: Level 1 — 연결 테스트 + LIMIT 5 SELECT
    """
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    # 커넥션 설정
    db = PostgreDB()

    # 연결 테스트
    logger.info(db.test_conn())

    # 쿼리 테스트
    query = f"SELECT * FROM {PostgreSqlTable.CRAWLING.value} LIMIT 5;"
    result = db.run_query(query)
    logger.info(result)


if __name__ == "__main__":
    main()
