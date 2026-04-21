from enum import Enum 


class CrawlingConstant():
    '''enum으로 정의하기 애매한 고정 상수 값을 정의하는 클래스'''
    PAGE_COUNT = 10
    REQUEST_DELAY_SECONDS = 0.5 # 연속 요청 간 간격(초). 서버 부하·차단 완화용
    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"



class PageURL(Enum):
    '''크롤링 대상 페이지 URL 주소를 정의하는 클래스'''
    GEEKNEWS = "https://news.hada.io/new"
    PYTORCH = "https://pytorch.org"

