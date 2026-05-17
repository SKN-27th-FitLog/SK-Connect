from __future__ import annotations

from enum import Enum

class Stage(Enum):
    '''작업 단계 표시 '''
    CRAWLING   = "raw"
    CLEANING    = "cleaning"
    SAVE        = "save"


class Status(Enum):
    '''저장시 파일 상태 표시'''
    SUCCESS = "success"
    FAIL = "fail"


class PathConst:
    '''저장경로 지정 시 폴더명 표시 '''
    DIR = "" #"etl/it_news"
    STAGE_KEY = "process"
    CODE_TABLE_KEY = "information_cd"
    YEAR_KEY = "year"
    MONTH_KEY = "month"
    DAY_KEY = "day"
    STATUS_KEY = "status"


class CrawlingConstant:
    """크롤·ETL·HTTP 등에 쓰는 스칼라 상수(열거가 어울리지 않을 때)."""

    PAGE_COUNT = 10
    REQUEST_DELAY_SECONDS = 0.5  # 연속 요청 간 간격(초). 서버 부하·차단 완화용
    # DB에 반영할 “마지막” 기준(워터마크)은 `get_last_success_date()` = `crawling.created_at` MAX(이미 넣은 글 중 가장 늦은 시각).
    # (행동일·활동일 등 다른 컬럼으로 워터마크를 바꿀 경우 이 주석과 `get_last_success_date` 쿼리만 맞추면 됨.)
    # DB가 비어 있을 때(최초 적재)만: 오늘로부터 n일 이전 00:00을 워터마크로 쓰고, 그 **이후**로 발행된 글만(행 필터) 대상 — n은 아래 n일.
    # raw=crawling run 폴더 하한·최초 워터마크 모두 아래 n일(클리닝·`default_last_collected_at`에서 동일 상수 사용).
    ETL_CRAWL_LOOKBACK_DAYS = 90
    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    # requests `headers=`, CSV 입출력, Discourse API 보조 URL
    USER_AGENT_HEADER = "User-Agent"
    CSV_ENCODING = "utf-8"
    PYTORCH_DISCOURSE_JSON_SUFFIX = ".json"
    # DB/크롤에서 조회수·점수·댓글 등 없을 때 쓰는 기본 정수(스키마·파싱 실패·미제공)
    DEFAULT_INT = 0


class ItNewsFilePrefix:
    """클리닝·save 단계 산출 CSV 파일명 prefix 기본값."""

    DEFAULT = "it_news"


class CrawlSourceToken:
    """크롤 소스 선택 시 ``Service`` slug 외의 특수 값(전체 실행)."""

    ALL = "all"


class Service(Enum):
    '''크롤링 대상 페이지 URL 주소를 정의하는 클래스'''
    GEEKNEWS = ("https://news.hada.io/new", "geeknews")
    PYTORCH = ("https://discuss.pytorch.kr/c/news/14/l/latest", "pytorch")


    @property # 속성 처럼 호출 
    def url(self) -> str:
        return self.value[0]

    @property # 속성 처럼 호출 
    def service(self) -> str:
        return self.value[1]


class CrawlingColumn(str, Enum):
    """크롤·클리닝·`crawling` INSERT 공통 DataFrame/행 키."""

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
    INFORMATION_CD = "information_cd"
    SHOP_CD = "shop_cd"
    KEYWORDS = "keywords"
    # 클리닝 파이프라인 전용(스키마 외)
    STATE = "state"
    PAGE_SERVICE = "_page_service"  # raw concat 시 출처 service 태그
    ERROR = "error"  # 크롤 per-URL 실패 메시지


class CategoryCdCode(str, Enum):
    """``crawling.category_cd`` 등 — ``database/data/codeT.csv`` (`cd_upper` = ``CA00``)."""

    GROUP = "CA00"
    RESTAURANT = "CA01"
    STUDY = "CA02"
    EXERCISE = "CA03"
    DAILY = "CA04"
    HOBBY = "CA05"
    FLEA_MARKET = "CA06"
    ETC = "CA07"


class InformationCdCode(str, Enum):
    """``crawling.information_cd`` 등 — ``database/data/codeT.csv`` (`cd_upper` = ``IC00``)."""

    GROUP = "IC00"
    RESTAURANT_INFO = "IC01"
    IT_INFO = "IC02"


class ShopCdCode(str, Enum):
    """``crawling.shop_cd`` / ``shop.shop_cd`` — ``database/data/codeT.csv`` (`cd_upper` = ``SC00``)."""

    GROUP = "SC00"
    KOREAN = "SC01"
    JAPANESE = "SC02"
    CHINESE = "SC03"
    WESTERN = "SC04"
    CAFE = "SC05"
    FUSION = "SC06"


class CodeTable(Enum):
    """it_news 파이프라인 기본 적재값(`CategoryCdCode` / `InformationCdCode`와 동일 문자열).

    - ``category_cd`` (행 데이터) → ``CategoryCdCode.ETC`` (IT 크롤 글은 커뮤니티 카테고리상 기타).
    - ``information_cd`` (행·``build_csv_path`` 세그먼트) → ``InformationCdCode.IT_INFO``.
    - ``shop_cd`` → 해당 없음 시 ``NULL`` (`ShopCdCode`는 맛집·가게 도메인 조회용).
    """

    CATEGORY_ETC = CategoryCdCode.ETC.value
    INFORMATION_IT = InformationCdCode.IT_INFO.value


class ItNewsLambdaEventKey:
    """Lambda ``event`` dict 키 이름."""

    SOURCE = "source"
    SAVE_FILE_PREFIX = "save_file_prefix"
    OUTPUT_CSV_PREFIX = "output_csv_prefix"


class ItNewsLambdaDefaults:
    """Lambda에서 해당 키가 없을 때 쓰는 기본값."""

    SOURCE = CrawlSourceToken.ALL
    SAVE_FILE_PREFIX = ItNewsFilePrefix.DEFAULT
    OUTPUT_CSV_PREFIX = ItNewsFilePrefix.DEFAULT
