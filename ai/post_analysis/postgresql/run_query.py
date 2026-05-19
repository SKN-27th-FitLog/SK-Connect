"""PostgreSQL에서 `crawling` / `analysis` 테이블을 읽고 MERGE하는 유틸."""

import numpy as np
import pandas as pd
from psycopg.types.json import Jsonb

from common.constant import AnalysisColumn
from postgresql.config import MergeAnalysisConfig, PostgreSqlTable
from postgresql.connection import PostgreDB


def get_crawling_data() -> pd.DataFrame:
    """`crawling` 테이블 전체를 DataFrame으로 반환한다."""
    db = PostgreDB()
    table = PostgreSqlTable.CRAWLING.value
    with db.conn.cursor() as cur:
        cur.execute(f"SELECT * FROM {table}")
        columns = [col.name for col in cur.description]
        rows = cur.fetchall()

    return pd.DataFrame(rows, columns=columns)


def get_analysis_data() -> pd.DataFrame:
    """`analysis` 테이블 전체를 DataFrame으로 반환한다."""
    db = PostgreDB()
    table = PostgreSqlTable.ANALYSIS.value
    with db.conn.cursor() as cur:
        cur.execute(f"SELECT * FROM {table}")
        columns = [col.name for col in cur.description]
        rows = cur.fetchall()

    return pd.DataFrame(rows, columns=columns)


def merge_analysis_data(df: pd.DataFrame) -> None:
    """DataFrame 행을 JSONB 레코드로 직렬화해 `analysis`에 UPSERT(MERGE)한다.

    ``NaN`` / ``pd.NA``는 ``None``으로 바꾸고, ``created_dt``는 ISO-like 문자열,
    bigint 후보 컬럼은 Nullable 정수로 맞춘 뒤 실행한다.

    Args:
        df: ``crawling_id``가 포함된 업서트 대상. 컬럼은 스키마에 맞게 전달한다.
    """
    merge_analysis_sql = MergeAnalysisConfig.MERGE_SQL

    db = PostgreDB()

    clean = df.replace({np.nan: None, pd.NA: None})
    clean = clean.where(pd.notnull(clean), None)

    created = AnalysisColumn.CREATED_DT.value
    if created in clean.columns:
        s = pd.to_datetime(clean[created], errors="coerce")
        clean[created] = s.dt.strftime(MergeAnalysisConfig.CREATED_DT_STRFTIME).where(
            s.notna(), None
        )

    for col in MergeAnalysisConfig.BIGINT_COLUMN_NAMES:
        if col in clean.columns:
            clean[col] = pd.to_numeric(clean[col], errors="coerce").astype("Int64")

    records = clean.to_dict(orient="records")

    with db.conn.cursor() as cur:
        cur.execute(merge_analysis_sql, (Jsonb(records),))
