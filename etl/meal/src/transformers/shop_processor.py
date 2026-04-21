from typing import Dict, List, Any, Optional
import json
import pandas as pd
from .base_processor import BaseProcessor
from ..core.file_manager import logger
from ..core.code_manager.resolver import CodeResolver
from ..core.constants import CodePrefix, MapsColumns, ShopColumns

class ShopProcessor(BaseProcessor):
    """
    식당 정보를 DB 적재 포맷으로 변환하며, 코드 리졸버를 통해 실시간으로 코드를 조회합니다.
    """
    
    def __init__(self, code_resolver: CodeResolver):
        super().__init__(code_resolver)
        # 기본 코드 설정 (Exact Match 정책)
        self.default_food_cd = self.resolver.resolve("기타", CodePrefix.FOOD) or "FC06"
        self.default_address_cd = "LA00" 
        self.map_category_cd = self.resolver.resolve("맛집", CodePrefix.CATEGORY) or "CA01"

    def resolve_address_cd(self, address: str) -> str:
        # 주소 문자열에서 시/구 추출하여 코드 조회 (단순화된 로직)
        for part in address.split():
             cd = self.resolver.resolve(part, CodePrefix.LOCATION)
             if cd: return cd
        return self.default_address_cd

    def resolve_food_category(self, source_category: str) -> str:
        # 카테고리 명칭으로 코드 조회
        cd = self.resolver.resolve(source_category, CodePrefix.FOOD)
        return cd if cd else self.default_food_cd

    def process_for_master(self, row: pd.Series, lat: Optional[float] = None, lon: Optional[float] = None) -> Dict[str, Any]:
        """마스터 테이블(maps, shop) 적재용 데이터 정제"""
        store_address = str(row.get("store_address", "")).strip()
        source_category = str(row.get("source_category", ""))
        
        return {
            MapsColumns.NAME.value: str(row.get("store_name", "")).strip(),
            MapsColumns.ADDRESS_DETAIL.value: store_address,
            "address_cd": self.resolve_address_cd(store_address),
            "food_category_cd": self.resolve_food_category(source_category),
            "maps_category_cd": self.map_category_cd,
            ShopColumns.RATING.value: self.safe_float(row.get("store_rating")),
            "menus_json": str(row.get("menus_json", "[]")),
            MapsColumns.LATITUDE.value: lat,
            MapsColumns.LONGITUDE.value: lon,
            MapsColumns.SOURCE_URL.value: str(row.get("store_url", ""))
        }

    def process_for_crawling(self, row: pd.Series) -> Dict[str, Any]:
        """crawling 테이블 적재용 데이터 정제"""
        from datetime import datetime
        name = str(row.get("store_name", "")).strip()
        address = str(row.get("store_address", ""))
        category = str(row.get("source_category", ""))
        
        content = f"주소: {address}\n카테고리: {category}"
        
        return {
            "title": name,
            "content": content,
            "thread": "shop",
            "article_url": str(row.get("store_url", "")),
            "created_at": datetime.now().strftime("%Y-%m-%d"),
            "view_count": 0,
            "comment_count": 0,
            "point": self.safe_float(row.get("store_rating")),
            "author": "crawler_bot",
            "category_cd": self.map_category_cd
        }
