from enum import Enum
from typing import Dict, List, Any, Optional, Final

class MapsColumns(Enum):
    MAP_ID: Final[str] = "map_id"
    NAME: Final[str] = "name"
    CATEGORY_CD: Final[str] = "category_cd"
    ADDRESS_CD: Final[str] = "address_cd"
    ADDRESS_DETAIL: Final[str] = "address_detail"
    LATITUDE: Final[str] = "latitude"
    LONGITUDE: Final[str] = "longitude"
    SOURCE_URL: Final[str] = "source_url"

class ShopColumns(Enum):
    SHOP_ID: Final[str] = "shop_id"
    MAP_ID: Final[str] = "map_id"
    CATEGORY_CD: Final[str] = "category_cd"
    RATING: Final[str] = "rating"
    KEYWORDS: Final[str] = "keywords"

class CrawlingColumns(Enum):
    CRAWLING_ID: Final[str] = "crawling_id"
    MAP_ID: Final[str] = "map_id"
    TITLE: Final[str] = "title"
    CONTENT: Final[str] = "content"
    THREAD: Final[str] = "thread"
    ARTICLE_URL: Final[str] = "article_url"
    CREATED_AT: Final[str] = "created_at"
    VIEW_COUNT: Final[str] = "view_count"
    COMMENT_COUNT: Final[str] = "comment_count"
    POINT: Final[str] = "point"
    AUTHOR: Final[str] = "author"
    CATEGORY_CD: Final[str] = "category_cd"

class MenuColumns(Enum):
    MENU_ID: Final[str] = "menu_id"
    SHOP_ID: Final[str] = "shop_id"
    NAME: Final[str] = "name"
    PRICE: Final[str] = "price"

class ImageColumns(Enum):
    IMAGE_ID: Final[str] = "image_id"
    IMAGE_URL: Final[str] = "image_url"
    TABLE_NAME: Final[str] = "table_name"
    TABLE_ID: Final[str] = "table_id"

# 스키마 계약 (Schema Contract)
SCHEMA_CONTRACT: Dict[str, Dict[str, Any]] = {
    "maps": {
        "columns": MapsColumns,
        "required": [MapsColumns.NAME, MapsColumns.ADDRESS_DETAIL, MapsColumns.LATITUDE, MapsColumns.LONGITUDE],
        "defaults": {},
        "nullable": [MapsColumns.ADDRESS_CD, MapsColumns.SOURCE_URL]
    },
    "shop": {
        "columns": ShopColumns,
        "required": [ShopColumns.MAP_ID, ShopColumns.CATEGORY_CD],
        "defaults": {ShopColumns.RATING: 0.0},
        "nullable": [ShopColumns.KEYWORDS]
    },
    "crawling": {
        "columns": CrawlingColumns,
        "required": [CrawlingColumns.TITLE, CrawlingColumns.THREAD, CrawlingColumns.ARTICLE_URL],
        "defaults": {
            CrawlingColumns.VIEW_COUNT: 0,
            CrawlingColumns.COMMENT_COUNT: 0,
            CrawlingColumns.POINT: 0.0,
            CrawlingColumns.AUTHOR: "crawler_bot"
        },
        "nullable": [CrawlingColumns.MAP_ID, CrawlingColumns.CONTENT]
    }
}
