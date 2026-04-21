from enum import Enum
from typing import Final, List

class CodePrefix(Enum):
    """코드 종류별 프리픽스 정의"""
    CATEGORY: Final[str] = "CA"     # 대분류 (RESTAURANT, STUDY 등)
    FOOD: Final[str] = "FC"         # 음식 분류 (KOREAN, JAPANESE 등)
    LOCATION: Final[str] = "LA"     # 지역 코드
    STATUS: Final[str] = "ST"       # 상태 코드

class LookupPolicy(Enum):
    """검색 실패 시 정책"""
    RAISE: Final[str] = "raise"     # 예외 발생
    FALLBACK_NONE: Final[str] = "none" # None 반환
    STRICT_PREFIX: Final[bool] = True  # 프리픽스 일치 여부 강제 체크
