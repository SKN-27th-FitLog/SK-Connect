import logging
from typing import List, Dict, Any
from sqlalchemy import text

from src.pipeline.stages.base_stage import BaseStage
from src.core.repository.database import db_manager
from src.core.constants import (
    QUERY_UPSERT_MAP, QUERY_UPSERT_SHOP, QUERY_INSERT_CRAWLING,
    QUERY_INSERT_MENU, QUERY_INSERT_IMAGE
)

class Stage4Load(BaseStage):
    """
    설계안 20장 준수 - Load Stage.
    정규화된 데이터를 DB에 영구 적재.
    """
    NAME = "load"

    def __init__(self, db=db_manager):
        super().__init__(self.NAME)
        self.db = db

    def execute(self, normalized_data: List[Dict[str, Any]], batch_id: str, category_cd: str) -> List[Dict[str, Any]]:
        results = []
        loaded_count = 0
        with self.db.get_session() as session:
            for record in normalized_data:
                store = record.get("store", {})
                try:
                    # 설계안 20장 준수 - 개별 레코드 트랜잭션 격리 (Savepoint 활용)
                    with session.begin_nested():
                        # 1. Integrity Check
                        if not store.get("address_cd") or store.get("address_cd") == "UNKNOWN":
                            raise ValueError(f"Invalid address_cd {store.get('address_cd')}")

                        # 2. Maps 적재
                        map_category = "CA01" 
                        map_id = session.execute(text(QUERY_UPSERT_MAP), {
                            "name": store["name"],
                            "category_cd": map_category,
                            "address_cd": store["address_cd"],
                            "address_detail": store["address_detail"],
                            "latitude": float(store.get("latitude", 0.0)),
                            "longitude": float(store.get("longitude", 0.0))
                        }).scalar()

                        # 3. Shop 적재
                        shop_id = session.execute(text(QUERY_UPSERT_SHOP), {
                            "map_id": map_id,
                            "shop_cd": store["shop_cd"],
                            "rating": float(store.get("rating", 0.0))
                        }).scalar()

                        # 4. Menu 적재
                        for menu in record.get("menus", []):
                            session.execute(text(QUERY_INSERT_MENU), {
                                "shop_id": shop_id,
                                "name": menu["name"],
                                "price": menu["price"]
                            })

                        # 5. Images 적재
                        for img in record.get("images", []):
                            # 파서가 dict({"url":...}) 또는 문자열을 반환할 수 있음
                            if isinstance(img, dict):
                                img_url = img.get("url", "")
                            else:
                                img_url = img
                            if not img_url:
                                continue
                            session.execute(text(QUERY_INSERT_IMAGE), {
                                "image_url": img_url,
                                "table_name": "shop",
                                "table_id": shop_id
                            })

                        # 6. Crawling 증거 및 리뷰 적재
                        session.execute(text(QUERY_INSERT_CRAWLING), {
                            "title": f"Crawl - {store['name']}",
                            "content": store.get("description", ""),
                            "article_url": store.get("canonical_url", ""),
                            "map_id": map_id,
                            "category_cd": "IC01",
                            "author": "System",
                            "keywords": "",
                            "point": float(store.get("rating", 0.0))
                        })

                        for review in record.get("reviews", []):
                            session.execute(text(QUERY_INSERT_CRAWLING), {
                                "title": f"Review - {store['name']}",
                                "content": review["content"],
                                "article_url": store.get("canonical_url", ""),
                                "map_id": map_id,
                                "category_cd": "IC01",
                                "author": review.get("author", "Anonymous"),
                                "keywords": ",".join(review.get("keywords", [])),
                                "point": float(review.get("rating", 0.0))
                            })
                        
                        loaded_count += 1
                        results.append({
                            "entity_id": store.get("entity_id"),
                            "status": "success",
                            "data": record
                        })
                except Exception as e:
                    self.logger.error(f"Failed to load record {store.get('name', 'Unknown')}: {e}")
                    results.append({
                        "entity_id": store.get("entity_id"),
                        "status": "fail",
                        "reason_code": "DB_LOAD_ERROR",
                        "detail": str(e),
                        "data": record
                    })
            
            session.commit()
            
        self.logger.info(f"Loaded {loaded_count} stores with related data to Normalized DB.")
        return results
