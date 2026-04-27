"""DB 실행 전용(INSERT 등). `crawling` 배치는 JSON 배열 1개로 `jsonb_to_recordset`에 넘긴다."""

import pandas as pd
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
INSERT INTO crawling (...)
SELECT * FROM jsonb_to_recordset($1::jsonb) AS t ( ... );
""".strip()  # 위 SQL 본문으로 치환

#####################################################################################################################
# 데이터 입력 시 에러 발생한 케이스가 있어서 추가로 넣은 예외 케이스 함수 (안정화 되면 클린징 단계로 옮겨야 함 )
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

# 만약 정의되지 않은 Column이 있는 경우 컬럼 단위로 일괄 처리하는 부분 
def _row_to_crawling_dict(row) -> dict:
    """DataFrame/Series 한 행 → INSERT용 dict. 없는 열은 None(키는 항상 CRAWLING_INSERT_COLS)."""
    d: dict = {}
    for col in CRAWLING_INSERT_COLS:
        if col not in row.index:  # Series - 하나의 데이터 row에 대해 해당 컬럼값이 없으면 None 처리 
            d[col] = None
        elif col == CrawlingColumn.MAP_ID.value: # map_id에 대한 특별 처리 (0값으로 썻더니 에러 발생해서 None으로 치환)
            d[col] = _normalize_map_id(row[col]) 
        else: # pandas의 결측치 표현만 None으로 치환 / 나머지는 유지 
            v = row[col]
            d[col] = None if (v is pd.NA or (isinstance(v, float) and pd.isna(v))) else v 
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