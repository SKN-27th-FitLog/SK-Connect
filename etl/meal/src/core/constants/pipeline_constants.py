from enum import Enum
from typing import Final

class CrawlerThread(Enum):
    """크롤링 스레드 구분"""
    SHOP: Final[str] = "shop"
    REVIEW: Final[str] = "review"

class LoadStatus(Enum):
    """결과 상태 코드"""
    SUCCESS: Final[str] = "success"
    FAIL: Final[str] = "fail"

class PlatformSource(Enum):
    """수집 플랫폼 코드"""
    DININGCODE: Final[str] = "DCODE"
