from typing import Dict, List, Any, Optional
import json
import pandas as pd
from .base_processor import BaseProcessor
from ..core.file_manager import logger

class ShopProcessor(BaseProcessor):
    """
    식당 정보를 DB 적재 및 전처리 포맷으로 변환하며, 데이터 무결성을 검증합니다.
    """
    
    def __init__(self, code_csv: str):
        self.category_map, self.address_map = self.load_code_tables(code_csv)
        self.default_food_cd = "FC06" # FUSION/기타
        self.default_address_cd = "LA00" # 기본 지역
        self.map_category_cd = "CA01" # RESTAURANT

    def resolve_address_cd(self, address: str) -> str:
        for name, cd in self.address_map.items():
            if name in address:
                return cd
        return self.default_address_cd

    def resolve_food_category(self, source_category: str) -> str:
        for name, cd in self.category_map.items():
            if name in source_category and cd.startswith("FC"):
                return cd
        return self.default_food_cd

    def validate_master_data(self, data: Dict[str, Any]) -> List[str]:
        """
        데이터 무결성을 검증합니다. 실패 시 실패 사유 리스트를 반환합니다.
        필수 요건: 주소, 좌표(lat, lon), 메뉴(최소 1건).
        """
        errors = []
        
        # 1. 주소 검증
        if not data.get("address_detail"):
            errors.append("Missing address_detail")
            
        # 2. 좌표 검증
        lat = data.get("latitude")
        lon = data.get("longitude")
        if lat is None or lon is None or (lat == 0.0 and lon == 0.0):
            errors.append("Invalid coordinates (0.0 or None)")
            
        # 3. 메뉴 검증
        try:
            menus = json.loads(data.get("menus_json", "[]"))
            if not menus:
                errors.append("No menu items found")
        except:
            errors.append("Menu data format error")
            
        return errors

    def process_for_master(self, row: pd.Series, lat: Optional[float] = None, lon: Optional[float] = None) -> Dict[str, Any]:
        """마스터 테이블(maps, shop) 적재용 데이터 정제"""
        store_address = str(row.get("store_address", "")).strip()
        source_category = str(row.get("source_category", ""))
        
        return {
            "name": str(row.get("store_name", "")).strip(),
            "address_detail": store_address,
            "address_cd": self.resolve_address_cd(store_address),
            "food_category_cd": self.resolve_food_category(source_category),
            "rating": self.safe_float(row.get("store_rating")),
            "menus_json": str(row.get("menus_json", "[]")),
            "latitude": lat,
            "longitude": lon,
            "shop_image_urls": str(row.get("shop_image_urls", "[]"))
        }

    def process_for_crawling(self, row: pd.Series) -> Dict[str, Any]:
        """crawling 테이블(thread='shop') 적재용 데이터 정제"""
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

    def process_batch_crawling(self, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty: return pd.DataFrame()
        records = [self.process_for_crawling(row) for _, row in df.iterrows()]
        return pd.DataFrame(records)
