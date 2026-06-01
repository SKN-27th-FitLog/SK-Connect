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
    """IC02 IT 뉴스 키워드 분석 배치 설정."""

    MODEL_ENV_KEY = "POST_ANALYSIS_IT_KEYWORDS_MODEL"
    OLLAMA_BASE_URL_ENV_KEY = "OLLAMA_BASE_URL"
    DEFAULT_MODEL = "gemma4:e4b"
    DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434"
    REQUEST_TIMEOUT_SECONDS = 300
    REQUEST_TIMEOUT_SECONDS_ENV_KEY = "POST_ANALYSIS_IT_KEYWORDS_TIMEOUT_SECONDS"
    MAX_CONTENT_CHARS_ENV_KEY = "POST_ANALYSIS_IT_KEYWORDS_MAX_CONTENT_CHARS"
    MAX_CONTENT_UNITS_ENV_KEY = "POST_ANALYSIS_IT_KEYWORDS_MAX_CONTENT_UNITS"
    MAX_UNIT_CHARS_ENV_KEY = "POST_ANALYSIS_IT_KEYWORDS_MAX_UNIT_CHARS"
    MAX_CONTENT_CHARS = 2500
    MAX_CONTENT_UNITS = 8
    MAX_UNIT_CHARS = 1200
    MIN_POSITIVE_CONFIG_VALUE = 1
    TITLE_PROMPT_LABEL = "[title]"
    CONTENT_PROMPT_LABEL = "[content]"
    COMPRESSED_CONTENT_PROMPT_LABEL = "[compressed_content]"
    CANDIDATE_PROMPT_LABEL = "[candidate_keywords]"
    INTEREST_PROMPT_LABEL = "[interest]"
    NORMALIZED_PARAGRAPH_SEPARATOR = "\n\n"
    PARAGRAPH_SPLIT_PATTERN = r"\n\s*\n+"
    LINE_BREAK_PATTERN = r"\r\n|\r"
    MULTI_BLANK_LINE_PATTERN = r"\n{3,}"
    INLINE_SPACE_PATTERN = r"[ \t\f\v]+"
    SENTENCE_SPLIT_PATTERN = r"(?<=[.!?。！？다요음함됨임])\s+|\n+"
    NUMBER_PATTERN = r"\d"
    WORD_PATTERN = r"[0-9A-Za-z가-힣]+"
    IMPORTANT_TERMS = (
        "AI",
        "LLM",
        "모델",
        "추론",
        "학습",
        "배포",
        "GPU",
        "CPU",
        "성능",
        "비용",
        "보안",
        "취약점",
        "릴리스",
        "버전",
        "업데이트",
        "프레임워크",
        "API",
        "오픈소스",
        "라이선스",
        "데이터",
        "개발자",
        "에이전트",
        "자동화",
        "클라우드",
        "인프라",
        "영향",
        "리스크",
        "사용",
    )
    PROMPT_INSTRUCTIONS = (
        "당신은 IT 뉴스 게시글 기획을 위한 키워드 분석기입니다.",
        "입력 글을 읽고 요약, 글의 흐름, 관심도 라벨, 게시글 생성용 키워드를 JSON으로만 반환하세요.",
        "입력 본문은 원문에서 발췌해 압축한 compressed_content입니다.",
        "키워드는 기술 주제와 게시글 독자 관점을 함께 포함해야 합니다.",
        "원문에 없는 인물, 사실, 제품명을 만들지 않습니다.",
        "JSON 외 텍스트를 출력하지 않습니다.",
    )
    PROMPT_SCHEMA_HEADER = "반환 JSON 스키마:"
    PROMPT_CONSTRAINTS_HEADER = "제약:"
    PROMPT_SUMMARY_GUIDE = (
        "- summary는 게시글 생성의 기반이 되는 3~5문장 분석 요약입니다. "
        "기술/프로젝트의 정체, 기존 대안 대비 차별점, 개발자/운영자의 실무 포인트를 반드시 포함합니다. "
        "원문에 제한사항, 테스트 단계, 주의사항이 있으면 반드시 포함하고, 원문에 없는 장점이나 안정성은 추정하지 않습니다."
    )
    PROMPT_KEYWORD_COUNT_TEMPLATE = "- keywords는 {min_keywords}개 이상 {max_keywords}개 이하입니다."
    PROMPT_KEYWORD_GUIDE = (
        "- keywords에는 기술명, 제품명, 프레임워크, 변경점, 영향, 리스크, 활용 포인트, 독자 관점을 균형 있게 넣습니다."
    )
    PROMPT_CANDIDATE_LIMIT_GUIDE = (
        "- keywords는 candidate_keywords에 있는 문자열만 사용합니다. 후보군 밖 새 키워드나 임의 합성어를 만들지 않습니다."
    )
    KEYWORD_EXPANSION_INSTRUCTIONS = (
        "이전 응답의 keywords가 너무 적습니다.",
        "원문에 근거한 세부 키워드를 12개 이상 15개 이하로 다시 나누세요.",
        "기술명, 변경점, 영향, 리스크, 활용 포인트, 독자 관점을 중복 없이 분리하세요.",
        "새 JSON만 반환하세요.",
    )
    KEYWORD_EXPANSION_PREVIOUS_LABEL = "[previous_response]"
    PROGRESS_DESC = "IC02 IT 키워드 추출"
    PROGRESS_UNIT = "건"
    RESPONSE_SCHEMA_EXAMPLE = (
        '{"summary":"릴리스 핵심 요약","flow":"발표 -> 변화 -> 영향",'
        '"interest_label":"high","keywords":["PyTorch 2.8","추론 성능 개선","GPU 비용",'
        '"배포 효율","API 변경","모델 최적화","서버 지연 시간","운영 비용",'
        '"개발자 영향","프로덕션 배포","성능 검토","AI 인프라"]}'
    )
    MIN_KEYWORDS = 12
    MAX_KEYWORDS = 15
    MAX_PROMPT_CANDIDATES = 40
    MIN_CANDIDATE_SCORE = 2
    CANDIDATE_MIN_KEYWORD_CHARS = 2
    CANDIDATE_MAX_KEYWORD_CHARS = 40
    CANDIDATE_TITLE_WEIGHT = 5
    CANDIDATE_EARLY_CONTENT_WEIGHT = 3
    CANDIDATE_FREQUENCY_WEIGHT = 2
    CANDIDATE_TECH_PATTERN_WEIGHT = 3
    CANDIDATE_IMPORTANT_TERM_WEIGHT = 2
    CANDIDATE_SIGNAL_NEARBY_WEIGHT = 2
    CANDIDATE_NOUN_POS_TAGS = ("NNG", "NNP", "SL", "SN")
    CANDIDATE_SIGNAL_POS_TAGS = ("VV", "VA", "XR")
    CANDIDATE_STOPWORDS = (
        "이해",
        "필요",
        "가능",
        "사용",
        "지원",
        "기반",
        "관련",
        "내용",
        "부분",
    )
    CANDIDATE_SIGNAL_TERMS = (
        "개선",
        "지원",
        "공개",
        "변경",
        "삭제",
        "검증",
        "자동화",
        "최적화",
        "절감",
        "통합",
        "배포",
        "확장",
    )
    DTYPE_OBJECT = "object"
    CONTENT_EMPTY_PLACEHOLDERS = ("", "-", "N/A")
    INTEREST_COMMENT_WEIGHT = 10
    INTEREST_POINT_WEIGHT = 20
    INTEREST_HIGH_THRESHOLD = 1000
    INTEREST_MEDIUM_THRESHOLD = 100


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
