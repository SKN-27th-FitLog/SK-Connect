from enum import Enum


class Stage(Enum):
    '''작업 단계 표시 '''
    CRAWLILNG   = "crawling"
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
    

class CrawlingConstant():
    '''enum으로 정의하기 애매한 고정 상수 값을 정의하는 클래스'''
    PAGE_COUNT = 10
    REQUEST_DELAY_SECONDS = 0.5 # 연속 요청 간 간격(초). 서버 부하·차단 완화용
    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"



class PageURL(Enum):
    '''크롤링 대상 페이지 URL 주소를 정의하는 클래스'''
    GEEKNEWS = ("https://news.hada.io/new", "geeknews")
    PYTORCH = ("https://discuss.pytorch.kr/c/news/14/l/latest", "pytorch")

    @property # 속성 처럼 호출 
    def url(self) -> str:
        return self.value[0]

    @property # 속성 처럼 호출 
    def service(self) -> str:
        return self.value[1]


class CodeTable(Enum):
    IT_NEWS = "CA07"
