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
    INFORMATION_CD = "information_cd"
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
                cls.INFORMATION_CD,
                cls.CREATED_DT,
                cls.SENTIMENTAL,
                cls.SCORE,
                cls.KEYWORDS,
                cls.POSITIVE_KW,
                cls.NEGATIVE_KW,
            }
        )


class CodeTable(str, Enum):
    """코드 테이블 문자열 참조(database/data/codeT, etl/it_news 규격과 동일).

    - ``CATEGORY_ETC`` (**CA07**): ``category_cd`` 축. IT 크롤 스트림에
      ``etl.it_news.common.constant.CategoryCdCode.ETC`` / ``CodeTable.CATEGORY_ETC`` 와 동일.
    - ``INFORMATION_IT_INFO`` (**IC02**): ``information_cd`` 축 IT 정보글.
      ``etl.it_news.common.constant.InformationCdCode.IT_INFO`` 와 동일.
    """

    CATEGORY_ETC = "CA07"
    INFORMATION_IT_INFO = "IC02"


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
