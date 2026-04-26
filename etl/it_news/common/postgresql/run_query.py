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


def insert_crawling_batch(df: pd.DataFrame, db: PostgreDB | None = None) -> None:
    """`crawling`에 df 전부를 1문(`unnest`)으로 INSERT. `df`는 위 열을 갖는다고 가정."""
    if df.empty:
        return
    conn = (db or PostgreDB()).conn
    # execute 두 번째 인자: 쿼리의 %s 개수(=12)와 맞는 튜플, 각 요소 = 한 열의 cell 리스트
    args = tuple(df[c].tolist() for c in CRAWLING_INSERT_COLS)
    with conn.cursor() as cur:
        cur.execute(INSERT_CRAWLING_UNNEST_SQL, args)
