from enum import Enum
from typing import Final

class Status(Enum):
    """
    게시글 및 사용자 상태 코드 (ST)
    - ACTIVE: 활성 상태
    - INACTIVE: 비활성 상태
    - DELETED: 삭제된 상태
    """
    ACTIVE: Final[str] = "ST01"
    INACTIVE: Final[str] = "ST02"
    DELETED: Final[str] = "ST03"

class PostType(Enum):
    """
    게시글 유형 코드 (PT)
    - GENERAL: 일반 게시글
    - COMMUNITY: 커뮤니티 게시글
    - OPERATIONAL: 운영 관련 (맛집리뷰, 공지사항 등)
    """
    GENERAL: Final[str] = "PT01"
    COMMUNITY: Final[str] = "PT02"
    OPERATIONAL: Final[str] = "PT03"

class Category(Enum):
    """
    주요 카테고리 코드 (CA)
    각 도메인별 대분류 서비스 코드를 정의합니다.
    """
    RESTAURANT: Final[str] = "CA01"
    STUDY: Final[str] = "CA02"
    SPORT: Final[str] = "CA03"
    DAILY: Final[str] = "CA04"
    HOBBY: Final[str] = "CA05"
    SHARE: Final[str] = "CA06"
    INFO: Final[str] = "CA07"
    ETC: Final[str] = "CA08"

class FoodCategory(Enum):
    """
    음식 분류 코드 (FC)
    맛집 정보의 상세 하위 분류를 정의합니다.
    """
    KOREAN: Final[str] = "FC01"     # 한식
    JAPANESE: Final[str] = "FC02"    # 일식
    CHINESE: Final[str] = "FC03"     # 중식
    WESTERN: Final[str] = "FC04"     # 양식
    CAFE: Final[str] = "FC05"        # 카페/디저트
    FUSION: Final[str] = "FC06"      # 퓨전/기타

class Location(Enum):
    """
    지역 대분류 기본 코드 (LA)
    지역 매핑의 기본이 되는 코드를 정의합니다.
    """
    DEFAULT: Final[str] = "LA00"

class TablePrefix(Enum):
    """
    테이블 식별 코드 접두사 (TC)
    DB 테이블 매핑 시 사용하는 접두사 코드입니다.
    """
    TABLE: Final[str] = "TC00"
    CODET: Final[str] = "TC01"
    USERS: Final[str] = "TC02"
    MAPS: Final[str] = "TC03"
    POSTS: Final[str] = "TC04"
    IMAGES: Final[str] = "TC05"
    COMMENTS: Final[str] = "TC06"
    LIKES: Final[str] = "TC07"
    SHOP: Final[str] = "TC08"
    MENU: Final[str] = "TC09"
    CRAWLING: Final[str] = "TC10"
