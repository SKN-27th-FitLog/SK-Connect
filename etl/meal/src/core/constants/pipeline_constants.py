from enum import Enum
from typing import Final

class CrawlerThread(Enum):
    """크롤링 스레드 구분"""
    SHOP: Final[str] = "shop"
    REVIEW: Final[str] = "review"

class ProcessType(Enum):
    """프로세스 구분"""
    CRAWLING: Final[str] = "crawling"
    CLEANING: Final[str] = "cleaning"
    SAVE: Final[str] = "save"

class Status(Enum):
    """DB 상태 코드 (ST)"""
    ACTIVE: Final[str] = "ST01"
    INACTIVE: Final[str] = "ST02"

class LoadStatus(Enum):
    """파일 저장 상태"""
    SUCCESS: Final[str] = "success"
    FAIL: Final[str] = "fail"

class PipelineQuota:
    """일일 수집 한도 설정"""
    DAILY_NEW_SHOP_LIMIT: Final[int] = 100 # 기본값
    RECOVERY_BATCH_LIMIT: Final[int] = 30
