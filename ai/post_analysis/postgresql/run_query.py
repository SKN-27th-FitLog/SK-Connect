"""PostgreSQL에서 `crawling` / `analysis` 테이블을 읽고 MERGE하는 유틸."""

# 패키지
import numpy as np
import pandas as pd
from psycopg.types.json import Jsonb

# 모듈
from common.constant import (
    AnalysisColumn,
    AnalyzeItKeywordsConfig,
    CodeTable,
)
from postgresql.config import MergeAnalysisConfig, PostgreSqlTable
from postgresql.connection import PostgreDB


def _read_query(sql: str, params: tuple[object, ...] = ()) -> pd.DataFrame:
    """지정 SQL을 실행해 DataFrame으로 반환한다."""
    db = PostgreDB()
    with db.conn.cursor() as cur:
        cur.execute(sql, params)
        columns = [col.name for col in cur.description]
        rows = cur.fetchall()
    return pd.DataFrame(rows, columns=columns)


##############################################
# 테이블 조회 쿼리를 내장 함수로 분리 
##############################################
def _read_table(table: str) -> pd.DataFrame:
    """지정 테이블을 ``SELECT *`` 로 읽어 DataFrame으로 반환한다.

    Args:
        table: PostgreSQL 테이블명 (호출부에서 ``PostgreSqlTable`` 등으로 전달).

    Returns:
        테이블 전체 행·컬럼 DataFrame.

    Note:
        함수 유형: D — 저장/조회
        안전성: Level 1 — 읽기 전용, 운영 DB 데이터 변경 없음
        부작용: DB SELECT, ``PostgreDB`` 연결 사용
    """
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
    """``crawling`` 테이블 전체를 읽어 DataFrame으로 반환한다.

    Returns:
        크롤링 원본 행. ``get_reviews`` 등 1단계 적재의 입력.

    Note:
        함수 유형: D — 저장/조회
        안전성: Level 1 — 읽기 전용
    """
    db = PostgreDB()
    table = PostgreSqlTable.CRAWLING.value
    # 컬럼값 까지 확인
    return _read_table(table)


##############################################
# 서버에서 shop 테이블 데이터 로드
##############################################
def get_shop_data() -> pd.DataFrame:
    """``shop`` 테이블 전체를 읽어 ``map_id`` → ``shop_id``/``shop_cd`` 조회에 사용한다.

    Returns:
        shop 마스터 DataFrame.

    Note:
        함수 유형: D — 저장/조회
        안전성: Level 1 — 읽기 전용
    """
    return _read_table(PostgreSqlTable.SHOP.value)


##############################################
# 서버에서 analysis 테이블 데이터 로드
##############################################
def get_analysis_data() -> pd.DataFrame:
    """``analysis`` 테이블 전체를 읽어 DataFrame으로 반환한다.

    Returns:
        분석 대상·결과 행. 감성·키워드 배치 및 중복 적재 판단의 입력.

    Note:
        함수 유형: D — 저장/조회
        안전성: Level 1 — 읽기 전용
    """
    db = PostgreDB()
    table = PostgreSqlTable.ANALYSIS.value
    return _read_table(table)


def get_it_keyword_target_data(
    *,
    overwrite: bool = False,
    max_rows: int | None = None,
) -> pd.DataFrame:
    """IC02 회사/감성 처리 대상 row만 조회한다."""
    text_placeholders = tuple(
        value for value in AnalyzeItKeywordsConfig.CONTENT_EMPTY_PLACEHOLDERS if value
    )
    text_placeholder_sql = ", ".join(["%s"] * len(text_placeholders))
    valid_title_sql = (
        "NULLIF(BTRIM(COALESCE(a.title, '')), '') IS NOT NULL "
        f"AND BTRIM(COALESCE(a.title, '')) NOT IN ({text_placeholder_sql})"
    )
    valid_content_sql = (
        "NULLIF(BTRIM(COALESCE(a.content, '')), '') IS NOT NULL "
        f"AND BTRIM(COALESCE(a.content, '')) NOT IN ({text_placeholder_sql})"
    )
    params: list[object] = [
        CodeTable.INFORMATION_IT_INFO.value,
        *text_placeholders,
        *text_placeholders,
    ]

    pending_condition = ""
    if not overwrite:
        pending_condition = (
            "\n      AND ("
            "\n        (a.sentimental IS NULL OR BTRIM(a.sentimental) = '')"
            "\n        OR a.score IS NULL"
            "\n      )"
        )

    limit_sql = ""
    if max_rows is not None:
        limit_sql = "\n    LIMIT %s"
        params.append(max_rows)

    sql = f"""
    SELECT
        a.{AnalysisColumn.CRAWLING_ID.value},
        a.{AnalysisColumn.TITLE.value},
        a.{AnalysisColumn.CONTENT.value},
        a.{AnalysisColumn.KEYWORDS.value},
        a.{AnalysisColumn.INFORMATION_CD.value},
        a.{AnalysisColumn.SENTIMENTAL.value},
        a.{AnalysisColumn.SCORE.value}
    FROM {PostgreSqlTable.ANALYSIS.value} AS a
    WHERE a.{AnalysisColumn.INFORMATION_CD.value} = %s
      AND (({valid_title_sql}) OR ({valid_content_sql})){pending_condition}
    ORDER BY a.{AnalysisColumn.CRAWLING_ID.value}{limit_sql}
    """
    return _read_query(sql, tuple(params))


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

    Note:
        함수 유형: D — 저장/조회 (UPSERT)
        안전성: Level 2 — ``analysis`` 행 insert/update, autocommit으로 즉시 반영
        불변 규칙: ``WHEN MATCHED`` 시 ``COALESCE(x.col, a.col)`` — NULL로 기존 값 덮어쓰지 않음
        부작용: PostgreSQL MERGE 실행
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
