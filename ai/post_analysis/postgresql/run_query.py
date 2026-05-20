"""PostgreSQL에서 `crawling` / `analysis` 테이블을 읽고 MERGE하는 유틸."""

# 패키지
import numpy as np
import pandas as pd
from psycopg.types.json import Jsonb

# 모듈
from common.constant import AnalysisColumn
from postgresql.config import MergeAnalysisConfig, PostgreSqlTable
from postgresql.connection import PostgreDB


def _read_table(table: str) -> pd.DataFrame:
    db = PostgreDB()
    with db.conn.cursor() as cur:
        cur.execute(f"SELECT * FROM {table}")
        columns = [col.name for col in cur.description]
        rows = cur.fetchall()
    return pd.DataFrame(rows, columns=columns)


##############################################
# 서버에서 crwaling 테이블 데이터 로드
##############################################
def get_crawling_data() -> pd.DataFrame:
    """crawling 테이블의 데이터를 서버로부터 읽어와서 데이터프레임으로 반환하는 함수.

    반환된 데이터 프레임은 이후 키워드 분석, 형태소 분해, 감정분류 등 처리를 위해 사용한다.
    해당 함수의 역할은 데이터 불러오기만 하는 용도로 사용.
    사용할 쿼리 현재 버전으로는 직접 정의해서 사용하되 나중에 범용 기능이 되면 분리 예정임.
    """
    db = PostgreDB()
    table = PostgreSqlTable.CRAWLING.value
    # 컬럼값 까지 확인
    return _read_table(table)


##############################################
# 서버에서 shop 테이블 데이터 로드
##############################################
def get_shop_data() -> pd.DataFrame:
    """`shop` 테이블 전체를 읽어 `map_id` → `shop_id`/`shop_cd` 조회에 사용한다."""
    return _read_table(PostgreSqlTable.SHOP.value)


##############################################
# 서버에서 analysis 테이블 데이터 로드
##############################################
def get_analysis_data() -> pd.DataFrame:
    """analysis 테이블의 데이터를 서버로부터 읽어와서 데이터프레임으로 반환하는 함수.

    반환된 데이터 프레임은 이후 키워드 분석, 형태소 분해, 감정분류 등 처리를 위해 사용한다.
    해당 함수의 역할은 데이터 불러오기만 하는 용도로 사용.
    사용할 쿼리 현재 버전으로는 직접 정의해서 사용하되 나중에 범용 기능이 되면 분리 예정임.
    """
    db = PostgreDB()
    table = PostgreSqlTable.ANALYSIS.value
    return _read_table(table)


##################################################################
# crawling 테이블에서 analysis 테이블로 한번에 데이터 merge
##################################################################
def merge_analysis_data(df: pd.DataFrame) -> None:
    """DataFrame 행을 JSONB 레코드로 직렬화해 `analysis`에 UPSERT(MERGE)한다.

    ``NaN`` / ``pd.NA``는 ``None``으로 바꾸고, ``created_dt``는 ISO-like 문자열,
    bigint 후보 컬럼은 Nullable 정수로 맞춘 뒤 실행한다.

    ``WHEN MATCHED`` 구간은 ``COALESCE(x.col, a.col)``로 기존 값을 보존하므로,
    단계별로 일부 컬럼만 담긴 DataFrame을 MERGE해도 NULL 덮어쓰기를 방지한다.

    Args:
        df: ``crawling_id``가 포함된 업서트 대상. 컬럼은 스키마에 맞게 전달한다.
    """
    # crawling 테이블과 analysis 테이블을 한번에 merge 하는 함수
    merge_analysis_sql = MergeAnalysisConfig.MERGE_SQL

    db = PostgreDB()

    # 데이터 입력 시 터질 수 있는 결측치 들 확인해서 처리
    clean = df.replace({np.nan: None, pd.NA: None})
    clean = clean.where(pd.notnull(clean), None)

    created = AnalysisColumn.CREATED_DT.value
    # 시간값인 경우 형식 변환
    if created in clean.columns:
        s = pd.to_datetime(clean[created], errors="coerce")
        clean[created] = s.dt.strftime(MergeAnalysisConfig.CREATED_DT_STRFTIME).where(
            s.notna(), None
        )

    # bigint 컬럼값 정수로 처리
    for col in MergeAnalysisConfig.BIGINT_COLUMN_NAMES:
        if col in clean.columns:
            clean[col] = pd.to_numeric(clean[col], errors="coerce").astype("Int64")

    # 처리된 데이터 다시 반환
    records = clean.to_dict(orient="records")

    with db.conn.cursor() as cur:
        cur.execute(merge_analysis_sql, (Jsonb(records),))
