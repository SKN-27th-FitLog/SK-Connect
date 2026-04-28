"""DB 실행 전용(INSERT 등). `crawling` 배치는 JSON 배열 1개로 `jsonb_to_recordset`에 넘긴다."""

import pandas as pd
import numpy as np
from psycopg.types.json import Jsonb  # psycopg3: jsonb 파라미터

from common.constant import CrawlingColumn
from common.postgresql.connection import PostgreDB

#################################################
# 데이터 테이블을 쿼리에 넣기 위한 사전 정의 
#################################################
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
    CrawlingColumn.KEYWORDS,
)
CRAWLING_INSERT_COLS: tuple[str, ...] = tuple(c.value for c in _CRAWLING_INSERT_ORDER)

INSERT_CRAWLING_FROM_JSONB_SQL = r"""
MERGE INTO crawling AS c
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
    keywords        varchar(100)
  )
) AS s
ON c.thread = s.thread
WHEN MATCHED THEN
  UPDATE SET
    title         = s.title,
    content       = s.content,
    article_url   = s.article_url,
    created_at    = s.created_at,
    view_count    = s.view_count,
    comment_count = s.comment_count,
    point         = s.point,
    author        = s.author,
    map_id        = s.map_id,
    category_cd   = s.category_cd,
    keywords      = s.keywords
WHEN NOT MATCHED THEN
  INSERT (
    title, content, thread, article_url, created_at,
    view_count, comment_count, point, author, map_id, category_cd, keywords
  )
  VALUES (
    s.title, s.content, s.thread, s.article_url, s.created_at,
    s.view_count, s.comment_count, s.point, s.author, s.map_id, s.category_cd, s.keywords
  );"""

#####################################################################################################################
# 데이터 입력 시 에러를 피하기 위한 보조: `_normalize_map_id`, `_to_json_value_temp` 등.
# INSERT 경로가 더 이상 타입·map_id 엣지에 의존하지 않게 되면, 행 정규화는 클리닝(또는 INSERT 직전 단일 레이어)으로 옮길 것.
#####################################################################################################################

# map_id 값을 0으로 했는데 에러 발생해서 None으로 치환 
def _normalize_map_id(v) -> int | None:
    if v is None or v is pd.NA or (isinstance(v, float) and pd.isna(v)):
        return None
    try:
        i = int(v)
    except (TypeError, ValueError):
        return None
    return None if i == 0 else i

# JSON으로 값을 넣을 때 받아주지 못하는 데이터 형식인 경우 데이터 값의 타입을 변환 
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


# 만약 정의되지 않은 Column이 있는 경우 컬럼 단위로 일괄 처리하는 부분 
def _row_to_crawling_dict(row) -> dict:
    """DataFrame/Series 한 행 → INSERT용 dict. 없는 열은 None(키는 항상 CRAWLING_INSERT_COLS)."""
    d: dict = {}
    for col in CRAWLING_INSERT_COLS:
        if col not in row.index:  # Series - 하나의 데이터 row에 대해 해당 컬럼값이 없으면 None 처리 
            d[col] = None
        elif col == CrawlingColumn.MAP_ID.value: # map_id에 대한 특별 처리 (0값으로 썻더니 에러 발생해서 None으로 치환)
            d[col] = _normalize_map_id(row[col]) 
        else: # 최종적으로 구해진 값을 처리하지 못하는 데이터 값이나 형식으로 받은 경우 처리 
            v = row[col]
            d[col] = _to_json_value_temp(v)
    return d

# 데이터 프레임의 데이터들을 row에 해당하는 dict 형태로 변환 
def _df_to_crawling_records(df: pd.DataFrame) -> list[dict]:
    return [_row_to_crawling_dict(df.iloc[i]) for i in range(len(df))]


#################################################
# 처리한 데이터 넣는 쿼리 실행 함수  
#################################################
def insert_crawling_batch(df: pd.DataFrame, db: PostgreDB | None = None) -> None:
    """`crawling`에 df 전부를 1문(`jsonb_to_recordset`)으로 INSERT."""
    if df.empty:
        return
    records = _df_to_crawling_records(df)
    conn = (db or PostgreDB()).conn
    # psycopg3: list[dict] → Jsonb로 jsonb 보냄. 또는 (json.dumps(records, default=str),) + SQL에서 ::jsonb
    payload = Jsonb(records)
    with conn.cursor() as cur:
        cur.execute(INSERT_CRAWLING_FROM_JSONB_SQL, (payload,))


#################################################
# crawling 테이블에서 지정한 컬럼의 값을 조회해 데이터 프레임으로 넘기는 함수 
#################################################
def fetch_crawling_dataframe(column: CrawlingColumn) -> pd.DataFrame:
    """crawling 테이블에서 지정한 컬럼의 값을 조회해 데이터 프레임으로 넘기는 함수"""
    db = PostgreDB()
    column_name = column.value
    with db.conn.cursor() as cur:
        cur.execute(f"SELECT {column_name} FROM crawling")
        return pd.DataFrame(cur.fetchall(), columns=[column_name])