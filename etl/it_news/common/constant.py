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
    DIR = "etl/it_news"
    STAGE_KEY = "raw"
    SERVICE_KEY = "service"
    YEAR_KEY = "year"
    MONTH_KEY = "month"
    DAY_KEY = "day"
    STATUS_KEY = "status"
