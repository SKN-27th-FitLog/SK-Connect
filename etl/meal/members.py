from enum import Enum

class Status(Enum):
    """게시글 및 사용자 상태 코드 (ST)"""
    ACTIVE = "ST01"
    INACTIVE = "ST02"
    DELETED = "ST03"

class PostType(Enum):
    """게시글 유형 코드 (PT)"""
    GENERAL = "PT01"
    COMMUNITY = "PT02"
    OPERATIONAL = "PT03" # 맛집리뷰, 공지사항 포함

class Category(Enum):
    """주요 카테고리 코드 (CA)"""
    RESTAURANT = "CA01"
    STUDY = "CA02"
    SPORT = "CA03"
    DAILY = "CA04"
    HOBBY = "CA05"
    SHARE = "CA06"
    INFO = "CA07"
    ETC = "CA08"

class FoodCategory(Enum):
    """음식 분류 코드 (FC)"""
    KOREAN = "FC01"
    JAPANESE = "FC02"
    CHINESE = "FC03"
    WESTERN = "FC04"
    CAFE = "FC05"
    FUSION = "FC06"

class Location(Enum):
    """지역 대분류 기본 코드 (LA)"""
    DEFAULT = "LA00"

class TablePrefix(Enum):
    """테이블 식별 코드 접두사 (TC)"""
    TABLE = "TC00"
    CODET = "TC01"
    USERS = "TC02"
    MAPS = "TC03"
    POSTS = "TC04"
    IMAGES = "TC05"
    COMMENTS = "TC06"
    LIKES = "TC07"
    SHOP = "TC08"
    MENU = "TC09"
    CRAWLING = "TC10"
