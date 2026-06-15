"""post_analysis 배치·DB·모델에서 공통으로 쓰는 컬럼명·코드·설정 상수."""

from __future__ import annotations

import re
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
        """DB/INSERT용으로 허용되는 본문 칼럼 집합(클리닝 전용·에러 필드 제외).

        Note:
            함수 유형: A — 순수 계산
            안전성: Level 0 — 외부 상태 접근·변경 없음
        """
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


class ShopColumn(str, Enum):
    """`shop` 테이블 DataFrame/행 키."""

    SHOP_ID = "shop_id"
    MAP_ID = "map_id"
    SHOP_CD = "shop_cd"


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
    SHOP_CD = "shop_cd"

    @classmethod
    def allowed_analysis_columns(cls) -> frozenset[str]:
        """파이프라인 MERGE SQL에 대응하는 분석 칼럼 집합.

        Note:
            함수 유형: A — 순수 계산
            안전성: Level 0 — 외부 상태 접근·변경 없음
        """
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
                cls.SHOP_CD,
                cls.CREATED_DT,
                cls.SENTIMENTAL,
                cls.SCORE,
                cls.KEYWORDS,
            }
        )


class CodeTable(str, Enum):
    """코드 테이블 문자열 참조(database/data/codeT, etl/it_news 규격과 동일).

    - ``CATEGORY_ETC`` (**CA07**): ``category_cd`` 축. IT 크롤 스트림에
      ``etl.it_news.common.constant.CategoryCdCode.ETC`` / ``CodeTable.CATEGORY_ETC`` 와 동일.
    - ``INFORMATION_IT_INFO`` (**IC02**): ``information_cd`` 축 IT 정보글.
      ``etl.it_news.common.constant.InformationCdCode.IT_INFO`` 와 동일.
    - ``INFORMATION_RESTAURANT`` (**IC01**): ``information_cd`` 축 맛집·리뷰 정보글.
      ``etl.it_news.common.constant.InformationCdCode.RESTAURANT_INFO`` 와 동일.
    """

    CATEGORY_ETC = "CA07"
    INFORMATION_RESTAURANT = "IC01"
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


class AnalyzeKeywordsByLlmConfig:
    """LLM 키워드 추출 배치(`analyze_keywords_by_llm`) 설정.

    LLM 호출 상한은 ``analyze_keywords_by_llm(max_rows=...)`` 인자로 제어한다.
    기본(``None``)은 제한 없음. 테스트·batch 청크 시에만 값을 넘긴다.
    """

    OPENAI_MODEL = "gpt-5.4-mini"
    DTYPE_OBJECT = "object"
    CONTENT_EMPTY_PLACEHOLDERS: tuple[str, ...] = ("", "-", "N/A")


class AnalyzeKeywordsConfig:
    """BERT span 키워드 추출 배치(`analyze_keywords`) 설정.

    처리 상한은 ``analyze_keywords(max_rows=...)`` 인자로 제어한다.
    """

    DTYPE_OBJECT = "object"
    CONTENT_EMPTY_PLACEHOLDERS: tuple[str, ...] = ("", "-", "N/A")


class AnalyzeItKeywordsConfig:
    """IC02 IT 뉴스 회사/분류 키워드와 제목 감성 처리 설정."""

    DEFAULT_WORKERS = 1
    MIN_POSITIVE_CONFIG_VALUE = 1
    MAX_KEYWORDS = 15
    BENCHMARK_DEFAULT_SAMPLE_ROWS = 20
    DTYPE_OBJECT = "object"
    CONTENT_EMPTY_PLACEHOLDERS = ("", "-", "N/A")


class BertKeywords:
    """BERT span 키워드 추출(`common/bert_keywords`) 설정."""

    MIN_WINDOW = 2
    MAX_WINDOW = 3
    TOP_K = 3
    SUBSPAN_SCORE_EPS = 0.05
    TOKEN_OPPOSITE_THRESHOLD = 0.5
    TOKEN_OPPOSITE_MARGIN = 0.025
    TOKEN_OPPOSITE_HIGH = 0.55
    TOKEN_OPPOSITE_MAX_LEN = 4
    MAX_TOKEN_LEN = 15
    MAX_SPAN_CHARS = 30

    STANDALONE_JAMO_TOKEN = re.compile(r"^[ㄱ-ㅎㅏ-ㅣ]+$")
    NON_WORD_CHARS = re.compile(r"[^\s\dA-Za-z가-힣]")
    MULTI_SPACE = re.compile(r"\s+")
    SENTIMENT_SHAPED_TOKEN = re.compile(r"(?:네요|습니다|어요|아요|해요|게|고|죠|냐)$")


class AnalyzeSentimentalConfig:
    """BERT 감성 분류 배치(`analyze_sentimental`) 및 `BertTokenizer` 기본값."""

    MODEL_NAME = "sangrimlee/bert-base-multilingual-cased-nsmc"
    MAX_SEQUENCE_LENGTH = 512
    SCORE_DECIMAL_PLACES = 4
    DTYPE_OBJECT = "object"
    DTYPE_SCORE = "float64"
    CONTENT_EMPTY_PLACEHOLDERS: tuple[str, ...] = ("", "-", "N/A")


class GetReviewsConfig:
    """크롤→분석 적재 배치(`get_reviews`)의 시간 문자열 형식."""

    ISOFORMAT_TIMESPEC = "seconds"
