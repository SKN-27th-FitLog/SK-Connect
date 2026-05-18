"""post_analysis 배치·DB·모델에서 공통으로 쓰는 컬럼명·코드·설정 상수."""

from __future__ import annotations

from enum import Enum


class CrawlingColumn(str, Enum):
    """크롤·클리닝·`crawling` INSERT 공통 DataFrame/행 키."""

    CRAWLING_ID = "crawling_id"
    TITLE = "title"
    CONTENT = "content"
    THREAD = "thread"
    ARTICLE_URL = "article_url"
    CREATED_AT = "created_at"
    VIEW_COUNT = "view_count"
    COMMENT_COUNT = "comment_count"
    POINT = "point"
    AUTHOR = "author"
    MAP_ID = "map_id"
    CATEGORY_CD = "category_cd"
    KEYWORDS = "keywords"
    # 클리닝 파이프라인 전용(스키마 외)
    STATE = "state"
    PAGE_SERVICE = "_page_service"  # raw concat 시 출처 service 태그
    ERROR = "error"  # 크롤 per-URL 실패 메시지

    @classmethod
    def allowed_crawling_columns(cls) -> frozenset[str]:
        """DB/INSERT용으로 허용되는 본문 칼럼 집합(클리닝 전용·에러 필드 제외)."""
        return frozenset(
            {
                cls.TITLE,
                cls.CONTENT,
                cls.THREAD,
                cls.ARTICLE_URL,
                cls.CREATED_AT,
                cls.VIEW_COUNT,
                cls.COMMENT_COUNT,
                cls.POINT,
                cls.AUTHOR,
                cls.MAP_ID,
                cls.CATEGORY_CD,
            }
        )


class AnalysisColumn(str, Enum):
    """분석·`INSERT analysis` 공통 DataFrame/행 키."""

    CRAWLING_ID = "crawling_id"
    TITLE = "title"
    CONTENT = "content"
    ARTICLE_URL = "article_url"
    MAP_ID = "map_id"
    SHOP_ID = "shop_id"
    CATEGORY_CD = "category_cd"
    CREATED_DT = "created_dt"
    SENTIMENTAL = "sentimental"
    SCORE = "score"
    KEYWORDS = "keywords"
    POSITIVE_KW = "positive_kw"
    NEGATIVE_KW = "negative_kw"

    @classmethod
    def allowed_analysis_columns(cls) -> frozenset[str]:
        """`analysis` MERGE 스키마에 대응하는 전체 분석 칼럼 집합."""
        return frozenset(
            {
                cls.CRAWLING_ID,
                cls.TITLE,
                cls.CONTENT,
                cls.ARTICLE_URL,
                cls.MAP_ID,
                cls.SHOP_ID,
                cls.CATEGORY_CD,
                cls.CREATED_DT,
                cls.SENTIMENTAL,
                cls.SCORE,
                cls.KEYWORDS,
                cls.POSITIVE_KW,
                cls.NEGATIVE_KW,
            }
        )


class CodeTable(str, Enum):
    """공통 도메인 코드 (`category_cd` 등)."""

    IT_NEWS = "IC02"


class SentimentLabel(str, Enum):
    """감성 분류 결과 라벨."""

    POSITIVE = "positive"
    NEGATIVE = "negative"


class SentimentResultKey(str, Enum):
    """`predict_sentiment` 등 결과 dict 키."""

    SENTIMENTAL = "sentimental"
    SCORE = "score"
    POSITIVE_SCORE = "positive_score"
    NEGATIVE_SCORE = "negative_score"


class KiwiPosTagPrefix(str, Enum):
    """kiwipiepy 토큰 태그 접두사(명사·동사·형용사 계열)."""

    NOUN_FAMILY = "N"
    VERB_FAMILY = "V"
    ADJECTIVE = "VA"


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


class KeywordFormat:
    """여러 파이프라인에서 동일하게 쓰는 키워드 토큰 구분자."""

    SEP = "#"


class AnalyzeKeywordsConfig:
    """형태소 기반 키워드 배치(`analyze_keywords`) 전용 pandas/LLM 외 설정."""

    DTYPE_OBJECT = "object"


class AnalyzeKeywordsByLlmConfig:
    """LLM 키워드 추출 배치(`analyze_keywords_by_llm`) 설정."""

    OPENAI_MODEL = "gpt-5.4-mini"
    DTYPE_OBJECT = "object"
    CONTENT_EMPTY_PLACEHOLDERS: tuple[str, ...] = ("", "-", "N/A")


class AnalyzeSentimentalConfig:
    """BERT 감성 분류 배치(`analyze_sentimental`) 및 `BertTokenizer` 기본값."""

    MODEL_NAME = "sangrimlee/bert-base-multilingual-cased-nsmc"
    MAX_SEQUENCE_LENGTH = 512
    SCORE_DECIMAL_PLACES = 4
    DTYPE_OBJECT = "object"
    DTYPE_SCORE = "float64"


class ClassifyKeywordsConfig:
    """감성 키워드 양분 배치(`classify_keywords`) 설정."""

    OPENAI_MODEL = "gpt-5.4-nano"
    PREVIEW_MAX_ROWS = 4


class GetReviewsConfig:
    """크롤→분석 적재 배치(`get_reviews`)의 시간 문자열 형식."""

    ISOFORMAT_TIMESPEC = "seconds"


class PostAnalysisLambdaStep(str, Enum):
    """Lambda 응답·로그에 쓰는 배치 단계 식별자."""

    GET_REVIEWS = "get_reviews"
    ANALYZE_SENTIMENTAL = "analyze_sentimental"
    ANALYZE_KEYWORDS_BY_LLM = "analyze_keywords_by_llm"


class PostAnalysisLambdaEventKey:
    """Lambda ``event`` dict 키 이름."""

    # ``analyze_keywords_by_llm`` 청크 실행용(양의 정수만 허용; 없으면 기존과 같이 전체)
    MAX_KEYWORD_ROWS = "max_keyword_rows"


class PostAnalysisLambdaResponseField:
    """``lambda_handler`` 반환 시 ``body`` dict 필드 이름."""

    STEP = "step"
    OK = "ok"
    ERROR = "error"


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
        crawling_id   bigint,
        title         varchar(500),
        content       text,
        article_url   varchar(500),
        map_id        bigint,
        shop_id       bigint,
        category_cd   varchar(6),
        created_dt    timestamp,
        sentimental   varchar(50),
        score         double precision,
        keywords      text,
        positive_kw   text,
        negative_kw   text
    )
    ) AS x
    ON a.crawling_id = x.crawling_id
    WHEN MATCHED THEN
    UPDATE SET
        title = x.title, content = x.content, article_url = x.article_url,
        map_id = x.map_id, shop_id = x.shop_id, category_cd = x.category_cd,
        created_dt = x.created_dt, sentimental = x.sentimental, score = x.score,
        keywords = x.keywords, positive_kw = x.positive_kw, negative_kw = x.negative_kw
    WHEN NOT MATCHED THEN
    INSERT (
        crawling_id, title, content, article_url, map_id, shop_id,
        category_cd, created_dt, sentimental, score, keywords, positive_kw, negative_kw
    )
    VALUES (
        x.crawling_id, x.title, x.content, x.article_url, x.map_id, x.shop_id,
        x.category_cd, x.created_dt, x.sentimental, x.score, x.keywords,
        x.positive_kw, x.negative_kw
    );
    """
