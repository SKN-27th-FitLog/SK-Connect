from typing import Dict, List, Any, Optional
from datetime import datetime
import pandas as pd
from .base_processor import BaseProcessor
from ..core.code_manager.resolver import CodeResolver
from ..core.constants.code_rules import CodePrefix

class ReviewProcessor(BaseProcessor):
    """
    수집된 리뷰 데이터를 crawling 테이블 형식에 맞게 변환하며, 키워드 데이터를 포함합니다.
    """
    
    def __init__(self, code_resolver: Optional[CodeResolver] = None):
        super().__init__(code_resolver)
        if self.resolver:
            self.default_category = self.resolver.resolve("맛집", CodePrefix.CATEGORY) or "CA01"
        else:
            self.default_category = "CA01"

    def process_for_crawling(self, row: pd.Series) -> Dict[str, Any]:
        """crawling 테이블 적재용 데이터 정제"""
        now = datetime.now()
        
        content = str(row.get("content", "")).strip()
        store_name = str(row.get("store_name", "식당"))
        
        return {
            "title": f"{store_name} 리뷰",
            "content": content,
            "thread": "review",
            "article_url": str(row.get("review_id", "")), # 식별자로 사용
            "created_at": str(row.get("date_text")) if pd.notna(row.get("date_text")) else now.strftime("%Y-%m-%d"),
            "view_count": 0,
            "comment_count": 0,
            "point": self.safe_float(row.get("rating")),
            "author": "crawler_bot",
            "keywords": row.get("keywords", "[]"),
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
