from __future__ import annotations

from enum import Enum

class Stage(Enum):
    '''작업 단계 표시 '''
    CRAWLING   = "crawling"
    CLEANING    = "cleaning"
    SAVE        = "save"


class Status(Enum):
    '''저장시 파일 상태 표시'''
    SUCCESS = "success"
    FAIL = "fail"


class PathConst:
    '''저장경로 지정 시 폴더명 표시 '''
    DIR = "" #"etl/it_news"
    STAGE_KEY = "raw"
    SERVICE_KEY = "service"
    YEAR_KEY = "year"
    MONTH_KEY = "month"
    DAY_KEY = "day"
    STATUS_KEY = "status"
    

class CrawlingConstant:
    """크롤·ETL·HTTP 등에 쓰는 스칼라 상수(열거가 어울리지 않을 때)."""

    PAGE_COUNT = 10
    REQUEST_DELAY_SECONDS = 0.5  # 연속 요청 간 간격(초). 서버 부하·차단 완화용
    # DB에 반영할 “마지막” 기준(워터마크)은 `get_last_success_date()` = `crawling.created_at` MAX(이미 넣은 글 중 가장 늦은 시각).
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


class Service(Enum):
    '''크롤링 대상 페이지 URL 주소를 정의하는 클래스'''
    GEEKNEWS = ("https://news.hada.io/new", "geeknews")
    PYTORCH = ("https://discuss.pytorch.kr/c/news/14/l/latest", "pytorch")
    IT_NEWS = ("", "it_news") # 클린징, 세이브에서 사용하는 범용 값 


    @property # 속성 처럼 호출 
    def url(self) -> str:
        return self.value[0]

    @property # 속성 처럼 호출 
    def service(self) -> str:
        return self.value[1]


class ThreadPrefix(str, Enum):
    """`crawling.thread` 및 소스별 `MAX(created_at)` 쿼리에 쓰는 접두."""

    GEEKNEWS = "geeknews_"
    PYTORCH = "pytorch_"

    @classmethod
    def for_crawl_source(cls, service: Service) -> ThreadPrefix:
        if service is Service.GEEKNEWS:
            return cls.GEEKNEWS
        if service is Service.PYTORCH:
            return cls.PYTORCH
        raise ValueError("ThreadPrefix: GEEKNEWS / PYTORCH만 지원")


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
    KEYWORDS = "keywords"
    # 클리닝 파이프라인 전용(스키마 외)
    STATE = "state"
    PAGE_SERVICE = "_page_service"  # raw concat 시 출처 service 태그
    ERROR = "error"  # 크롤 per-URL 실패 메시지


class CodeTable(Enum):
    IT_NEWS = "CA07"
