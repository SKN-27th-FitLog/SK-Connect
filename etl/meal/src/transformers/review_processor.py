from typing import Dict, List, Any
from datetime import datetime
import pandas as pd
from .base_processor import BaseProcessor

class ReviewProcessor(BaseProcessor):
    """
    수집된 리뷰 데이터를 crawling 테이블 형식에 맞게 변환합니다.
    """
    
    def __init__(self):
        super().__init__()
        self.default_category = "CA01" # 맛집(RESTAURANT)

    def process_for_crawling(self, row: pd.Series) -> Dict[str, Any]:
        """crawling 테이블 적재용 데이터 정제"""
        now = datetime.now()
        
        content = str(row.get("content", "")).strip()
        store_name = str(row.get("store_name", "식당"))
        
        return {
            "title": f"{store_name} 리뷰",
            "content": content,
            "thread": "review",
            "article_url": str(row.get("store_url", "")),
            "created_at": str(row.get("date")) if pd.notna(row.get("date")) else now.strftime("%Y-%m-%d"),
            "view_count": 0,
            "comment_count": 0,
            "point": self.safe_float(row.get("rating")),
            "author": "crawler_bot",
            "map_id": None, # Loader에서 조회하여 채울 예정
            "local_image_paths": row.get("local_image_paths", "[]"),
            "category_cd": self.default_category
        }

    def process_batch(self, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            return pd.DataFrame()
            
        processed_records = []
        for _, row in df.iterrows():
            if not str(row.get("content", "")).strip():
                continue
            processed_records.append(self.process_for_crawling(row))
            
        return pd.DataFrame(processed_records)
