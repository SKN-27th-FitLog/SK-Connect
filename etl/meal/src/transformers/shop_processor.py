from typing import Dict, List, Any
import pandas as pd
from .base_processor import BaseProcessor

class ShopProcessor(BaseProcessor):
    """
    식당 정보를 DB 적재 및 전처리 포맷으로 변환합니다.
    """
    
    def __init__(self, code_csv: str):
        self.category_map, self.address_map = self.load_code_tables(code_csv)
        self.default_food_cd = "FC06" # FUSION/기타
        self.default_address_cd = "LA00" # 기본 지역

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

    def process_for_master(self, row: pd.Series) -> Dict[str, Any]:
        """마스터 테이블(maps, shop) 적재용 데이터 정제"""
        store_address = str(row.get("store_address", ""))
        source_category = str(row.get("source_category", ""))
        
        return {
            "name": str(row.get("store_name", "")).strip(),
            "address_detail": store_address,
            "address_cd": self.resolve_address_cd(store_address),
            "food_category_cd": self.resolve_food_category(source_category),
            "rating": self.safe_float(row.get("store_rating")),
            "menus_json": row.get("menus_json", "[]")
        }

    def process_for_crawling(self, row: pd.Series) -> Dict[str, Any]:
        """crawling 테이블(thread='shop') 적재용 데이터 정제"""
        from datetime import datetime
        name = str(row.get("store_name", "")).strip()
        address = str(row.get("store_address", ""))
        category = str(row.get("source_category", ""))
        
        # content 본문 생성 (기존 규약 준수)
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
            "category_cd": "CA01" # 맛집 고정
        }

    def process_batch_crawling(self, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty: return pd.DataFrame()
        records = [self.process_for_crawling(row) for _, row in df.iterrows()]
        return pd.DataFrame(records)
