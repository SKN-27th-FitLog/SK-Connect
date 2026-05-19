"""PostgreSQL 환경변수·테이블명·MERGE SQL 등 DB 전용 상수."""

from __future__ import annotations

from enum import Enum

from common.constant import AnalysisColumn


class PostgreSqlTable(str, Enum):
    """post_analysis PostgreSQL 테이블 이름."""

    CRAWLING = "crawling"
    ANALYSIS = "analysis"


class PostgresEnvKey(str, Enum):
    """`.env` 기반 연결 환경변수 키."""

    USER = "PGUSER"
    PASSWORD = "PGPASSWORD"
    HOST = "PGHOST"
    PORT = "PGPORT"
    DATABASE = "PGDATABASE"


class MergeAnalysisConfig:
    """`merge_analysis_data`에서 쓰는 SQL·타입 정규화 상수."""

    CREATED_DT_STRFTIME = "%Y-%m-%dT%H:%M:%S"
    BIGINT_COLUMN_NAMES: tuple[str, ...] = (
        AnalysisColumn.CRAWLING_ID.value,
        AnalysisColumn.MAP_ID.value,
        AnalysisColumn.SHOP_ID.value,
    )
    MERGE_SQL: str = r"""
    MERGE INTO analysis AS a
    USING (
    SELECT * FROM jsonb_to_recordset(%s::jsonb) AS s (
        crawling_id     bigint,
        title           varchar(500),
        content         text,
        article_url     varchar(500),
        map_id          bigint,
        shop_id         bigint,
        category_cd     varchar(6),
        information_cd  varchar(6),
        created_dt      timestamp,
        sentimental     varchar(50),
        score           double precision,
        keywords        text,
        positive_kw     text,
        negative_kw     text
    )
    ) AS x
    ON a.crawling_id = x.crawling_id
    WHEN MATCHED THEN
    UPDATE SET
        title = COALESCE(x.title, a.title),
        content = COALESCE(x.content, a.content),
        article_url = COALESCE(x.article_url, a.article_url),
        map_id = COALESCE(x.map_id, a.map_id),
        shop_id = COALESCE(x.shop_id, a.shop_id),
        category_cd = COALESCE(x.category_cd, a.category_cd),
        information_cd = COALESCE(x.information_cd, a.information_cd),
        created_dt = COALESCE(x.created_dt, a.created_dt),
        sentimental = COALESCE(x.sentimental, a.sentimental),
        score = COALESCE(x.score, a.score),
        keywords = COALESCE(x.keywords, a.keywords),
        positive_kw = COALESCE(x.positive_kw, a.positive_kw),
        negative_kw = COALESCE(x.negative_kw, a.negative_kw)
    WHEN NOT MATCHED THEN
    INSERT (
        crawling_id, title, content, article_url, map_id, shop_id,
        category_cd, information_cd, created_dt, sentimental, score,
        keywords, positive_kw, negative_kw
    )
    VALUES (
        x.crawling_id, x.title, x.content, x.article_url, x.map_id, x.shop_id,
        x.category_cd, x.information_cd, x.created_dt, x.sentimental, x.score,
        x.keywords, x.positive_kw, x.negative_kw
    );
    """
