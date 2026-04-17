from enum import Enum
from typing import Final

class Category(Enum):
    """주요 카테고리 코드 (CA)"""
    RESTAURANT: Final[str] = "CA01"
    STUDY: Final[str] = "CA02"

class FoodCategory(Enum):
    """음식 분류 코드 (FC)"""
    KOREAN: Final[str] = "FC01"
    JAPANESE: Final[str] = "FC02"
    CHINESE: Final[str] = "FC03"
    WESTERN: Final[str] = "FC04"
    CAFE: Final[str] = "FC05"
    FUSION: Final[str] = "FC06"

class CrawlerThread(Enum):
    """크롤링 스레드 구분"""
    SHOP: Final[str] = "shop"
    REVIEW: Final[str] = "review"

class Status(Enum):
    """상태 코드"""
    ACTIVE: Final[str] = "ST01"
    INACTIVE: Final[str] = "ST02"

class LoadStatus(Enum):
    """적재 및 파일 저장 상태"""
    SUCCESS: Final[str] = "success"
    FAIL: Final[str] = "fail"
