"""`crawling` 테이블 워터마크(`MAX(created_at)`) 조회."""

from __future__ import annotations

from datetime import datetime

from common.constant import Service
from common.errors import EtlErrors
from common.utils import default_last_collected_at
from postgresql.config import SQL_MAX_CREATED_AT_ALL, SQL_MAX_CREATED_AT_BY_THREAD_PREFIX
from postgresql.connection import PostgreDB


def get_last_success_date(service: Service | None = None) -> datetime:
    """`crawling` 테이블 `MAX(created_at)` 워터마크를 조회한다.

    Note:
        함수 유형: D — DB 조회
        안전성: Level 1
        불변 규칙: row 없음→`default_last_collected_at()`; service는 GEEKNEWS/PYTORCH 또는 None(전체)
        부작용: PostgreSQL SELECT
    """
    if service is None:
        conn = PostgreDB()
        max_rows = conn.run_query(SQL_MAX_CREATED_AT_ALL)
        raw = max_rows[0][0] if max_rows else None
    elif service in (Service.GEEKNEWS, Service.PYTORCH):
        pat = f"^{service.service}_"
        conn = PostgreDB()
        max_rows = conn.run_query_lst(SQL_MAX_CREATED_AT_BY_THREAD_PREFIX, (pat,))
        raw = max_rows[0][0] if max_rows else None
    else:
        raise ValueError(EtlErrors.Watermark.unsupported_service(service))

    if raw is None:
        return default_last_collected_at()
    return raw
