"""DB 실행 전용(INSERT 등). `unnest` 일괄 INSERT는 `%%s` 자리가 열 개수만큼 있어, 열당 Python `list`를 인자로 넘긴다."""
from __future__ import annotations

import pandas as pd

from common.postgresql.connection import PostgreDB

# crawling_id 제외(시퀀스). df는 이 열 순서·이름으로 맞춰진 상태로 넘긴다.
CRAWLING_INSERT_COLS: tuple[str, ...] = (
    "title",
    "content",
    "thread",
    "article_url",
    "created_at",
    "view_count",
    "comment_count",
    "point",
    "author",
    "map_id",
    "category_cd",
    "keywords",
)

INSERT_CRAWLING_UNNEST_SQL = """
INSERT INTO crawling (title, content, thread, article_url, created_at, view_count, comment_count, point, author, map_id, category_cd, keywords)
SELECT * FROM unnest(
  %s::varchar(200)[],
  %s::text[],
  %s::varchar(20)[],
  %s::varchar(500)[],
  %s::timestamp[],
  %s::integer[],
  %s::integer[],
  %s::double precision[],
  %s::varchar(100)[],
  %s::bigint[],
  %s::varchar(6)[],
  %s::varchar(100)[]
) AS t(
  title, content, thread, article_url, created_at, view_count, comment_count,
  point, author, map_id, category_cd, keywords
)
"""

# 
def _list_for_col(df: pd.DataFrame, col: str, n: int) -> list:
    """INSERT 컬럼 한 열에 대응하는 값 list. `map_id=0`은 `maps` FK에 없으므로 NULL(크롤 기본값)."""
    if col not in df.columns:
        return [None] * n
    if col != "map_id":
        return df[col].tolist()
    out: list = []
    for v in df[col].tolist():
        if v is None or v is pd.NA or (isinstance(v, float) and pd.isna(v)):
            out.append(None)
            continue
        try:
            i = int(v)
        except (TypeError, ValueError):
            out.append(None)
            continue
        out.append(None if i == 0 else i)
    return out


def insert_crawling_batch(df: pd.DataFrame, db: PostgreDB | None = None) -> None:
    """`crawling`에 df 전부를 1문(`unnest`)으로 INSERT. DB에 있으나 df에 없는 열(예: keywords)은 NULL로 채움."""
    if df.empty:
        return
    conn = (db or PostgreDB()).conn
    n = len(df)
    args = tuple(_list_for_col(df, c, n) for c in CRAWLING_INSERT_COLS)
    with conn.cursor() as cur:
        cur.execute(INSERT_CRAWLING_UNNEST_SQL, args)
