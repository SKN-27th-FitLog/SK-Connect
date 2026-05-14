from __future__ import annotations

from enum import Enum


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

    @classmethod
    def allowed_crawling_columns(cls) -> frozenset[str]:
        return frozenset({cls.TITLE, cls.CONTENT, cls.THREAD, cls.ARTICLE_URL, cls.CREATED_AT, cls.VIEW_COUNT, cls.COMMENT_COUNT, cls.POINT, cls.AUTHOR, cls.MAP_ID, cls.CATEGORY_CD})

class AnalysisColumn(str, Enum):
    """분석·`analysis` INSERT 공통 DataFrame/행 키."""
    CRAWLING_ID = "crawling_id"
    TITLE = "title"
    CONTENT = "content"
    ARTICLE_URL = "article_url"
    MAP_ID = "map_id"
    SHOP_ID = "shop_id"
    CATEGORY_CD = "category_cd"
    CREATED_DT = "created_dt"
    SENTIMENTAL = "sentimental"
    SCORE = "score"
    KEYWORDS = "keywords"
    POSITIVE_KW = "positive_kw"
    NEGATIVE_KW = "negative_kw"

    @classmethod
    def allowed_analysis_columns(cls) -> frozenset[str]:
        return frozenset({cls.CRAWLING_ID, cls.TITLE, cls.CONTENT, cls.ARTICLE_URL, cls.MAP_ID, cls.SHOP_ID, cls.CATEGORY_CD, cls.CREATED_DT, cls.SENTIMENTAL, cls.SCORE, cls.KEYWORDS, cls.POSITIVE_KW, cls.NEGATIVE_KW})


class CodeTable(Enum):
    IT_NEWS = "IC02"
