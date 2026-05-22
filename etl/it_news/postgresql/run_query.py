"""DB 실행 전용(INSERT 등). `crawling` 배치는 JSON 배열 1개로 `jsonb_to_recordset`에 넘긴다."""

from __future__ import annotations

import numpy as np
import pandas as pd
from psycopg.types.json import Jsonb

from common.constant import CrawlingColumn
from postgresql.config import TABLE_CRAWLING
from postgresql.connection import PostgreDB

_CRAWLING_INSERT_ORDER: tuple[CrawlingColumn, ...] = (
    CrawlingColumn.TITLE,
    CrawlingColumn.CONTENT,
    CrawlingColumn.THREAD,
    CrawlingColumn.ARTICLE_URL,
    CrawlingColumn.CREATED_AT,
    CrawlingColumn.VIEW_COUNT,
    CrawlingColumn.COMMENT_COUNT,
    CrawlingColumn.POINT,
    CrawlingColumn.AUTHOR,
    CrawlingColumn.MAP_ID,
    CrawlingColumn.CATEGORY_CD,
    CrawlingColumn.INFORMATION_CD,
    CrawlingColumn.SHOP_CD,
    CrawlingColumn.KEYWORDS,
)
CRAWLING_INSERT_COLS: tuple[str, ...] = tuple(c.value for c in _CRAWLING_INSERT_ORDER)

INSERT_CRAWLING_FROM_JSONB_SQL = f"""
MERGE INTO {TABLE_CRAWLING} AS c
USING (
  SELECT * FROM jsonb_to_recordset(%s::jsonb) AS t (
    title           varchar(200),
    content         text,
    thread          varchar(20),
    article_url     varchar(500),
    created_at      timestamp,
    view_count      integer,
    comment_count   integer,
    point           double precision,
    author          varchar(100),
    map_id          bigint,
    category_cd     varchar(6),
    information_cd  varchar(6),
    shop_cd         varchar(6),
    keywords        varchar(100)
  )
) AS s
ON c.thread = s.thread
WHEN MATCHED THEN
  UPDATE SET
    title           = s.title,
    content         = s.content,
    article_url     = s.article_url,
    created_at      = s.created_at,
    view_count      = s.view_count,
    comment_count   = s.comment_count,
    point           = s.point,
    author          = s.author,
    map_id          = s.map_id,
    category_cd     = s.category_cd,
    information_cd  = s.information_cd,
    shop_cd         = s.shop_cd,
    keywords        = s.keywords
WHEN NOT MATCHED THEN
  INSERT (
    title, content, thread, article_url, created_at,
    view_count, comment_count, point, author, map_id, category_cd,
    information_cd, shop_cd, keywords
  )
  VALUES (
    s.title, s.content, s.thread, s.article_url, s.created_at,
    s.view_count, s.comment_count, s.point, s.author, s.map_id, s.category_cd,
    s.information_cd, s.shop_cd, s.keywords
  );"""


def _normalize_map_id(v) -> int | None:
    if v is None or v is pd.NA or (isinstance(v, float) and pd.isna(v)):
        return None
    try:
        i = int(v)
    except (TypeError, ValueError):
        return None
    return None if i == 0 else i


def _to_json_value_temp(v: object) -> object:
    """JSON/Jsonb 직렬화용으로 스칼라 정리(임시). numpy/pandas → int/float/str, 실패 시 str."""
    if v is None or v is pd.NA:
        return None
    if isinstance(v, float) and pd.isna(v):
        return None
    try:
        if isinstance(v, pd.Timestamp):
            return None if pd.isna(v) else v.isoformat()
        if isinstance(v, (np.integer, int)) and not isinstance(v, bool):
            return int(v)
        if isinstance(v, (np.floating, float)) and not isinstance(v, bool):
            x = float(v)
            if np.isnan(x) or np.isinf(x):
                return None
            return x
        if isinstance(v, (str, type(None), bool)):
            return v
        if hasattr(v, "item") and not isinstance(v, (str, bytes, dict, list, pd.Timestamp)):
            return _to_json_value_temp(v.item())
    except (TypeError, ValueError, AttributeError, OverflowError):
        pass
    try:
        return str(v) if v is not None and v is not pd.NA else None
    except Exception:
        return None


def _row_to_crawling_dict(row) -> dict:
    d: dict = {}
    for col in CRAWLING_INSERT_COLS:
        if col not in row.index:
            d[col] = None
        elif col == CrawlingColumn.MAP_ID.value:
            d[col] = _normalize_map_id(row[col])
        else:
            d[col] = _to_json_value_temp(row[col])
    return d


def _df_to_crawling_records(df: pd.DataFrame) -> list[dict]:
    return [_row_to_crawling_dict(df.iloc[i]) for i in range(len(df))]


def insert_crawling_batch(df: pd.DataFrame, db: PostgreDB | None = None) -> None:
    """DataFrame을 JSON 배열로 `crawling`에 MERGE·INSERT한다.

    Note:
        함수 유형: D — DB 저장
        안전성: Level 2
        불변 규칙: `ON thread` MATCHED UPDATE / NOT MATCHED INSERT; 빈 df는 no-op
        부작용: 운영 DB `crawling` 변경
    """
    if df.empty:
        return
    records = _df_to_crawling_records(df)
    conn = (db or PostgreDB()).conn
    payload = Jsonb(records)
    with conn.cursor() as cur:
        cur.execute(INSERT_CRAWLING_FROM_JSONB_SQL, (payload,))


def fetch_crawling_dataframe(column: CrawlingColumn) -> pd.DataFrame:
    """`crawling`에서 단일 컬럼을 SELECT해 DataFrame으로 반환한다.

    Note:
        함수 유형: D — DB 조회
        안전성: Level 1
        부작용: PostgreSQL SELECT
    """
    db = PostgreDB()
    column_name = column.value
    with db.conn.cursor() as cur:
        cur.execute(f"SELECT {column_name} FROM {TABLE_CRAWLING}")
        return pd.DataFrame(cur.fetchall(), columns=[column_name])
