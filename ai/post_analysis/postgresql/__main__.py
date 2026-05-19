"""DB 연결·샘플 쿼리 검증: ``python -m postgresql``."""

import logging

from postgresql.config import PostgreSqlTable
from postgresql.connection import PostgreDB


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    db = PostgreDB()
    logger.info(db.test_conn())

    query = f"SELECT * FROM {PostgreSqlTable.CRAWLING.value} LIMIT 5;"
    result = db.run_query(query)
    logger.info(result)


if __name__ == "__main__":
    main()
