import logging
from typing import List, Dict, Any
from sqlalchemy import text
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from src.core.base_stage import BaseStage
from src.core.repository.database import db_manager
from src.core.repository.code_table_repository import CodeTableRepository, code_repo
from src.core.policy.reason_code import ReasonCode
from src.core.policy.exceptions import UndefinedCodeException
from src.core.constants import (
    QUERY_UPSERT_MAP, QUERY_UPSERT_SHOP, QUERY_INSERT_CRAWLING,
    QUERY_INSERT_MENU, QUERY_INSERT_IMAGE
)

class Stage4Load(BaseStage):
    """
    [설계안 20 일치] - Load Stage.
    정규화된 데이터를 DB에 영구 적재.
    설계안 17. Load / Transaction 경계 및 "Stage 4 Load 전 코드 테이블 참조 무결성 재검증" 위반 사항 해소.
    """
    NAME = "load"

    def __init__(self, db=db_manager, code_repository: CodeTableRepository = code_repo):
        super().__init__(self.NAME)
        self.db = db
        self.code_repo = code_repository

    def _validate_required_codes(self, store: Dict[str, Any], category_cd: str):
        """DB 적재 전 필수 제약조건 및 코드 테이블 물리적 참조 무결성 재검증"""
        addr_cd = store.get("address_cd")
        shop_cd = store.get("shop_cd")
        
        # Address 검증
        if not addr_cd or addr_cd == "UNKNOWN" or not self.code_repo.get_address_info(addr_cd):
            raise UndefinedCodeException(
                reason_code=ReasonCode.UNDEFINED_CODE_DETECTED,
                stage=self.NAME,
                entity_type="store",
                detail=f"address_cd is missing, UNKNOWN, or invalid in CodeTable: {addr_cd}"
            )
            
        # Shop Code 검증
        if not shop_cd or not self.code_repo.get_shop_code(shop_cd):
            raise UndefinedCodeException(
                reason_code=ReasonCode.UNDEFINED_CODE_DETECTED,
                stage=self.NAME,
                entity_type="store",
                detail=f"shop_cd is missing or invalid in CodeTable: {shop_cd}"
            )
            
        # Category Code 검증 (부여받은 상위 분류 카테고리)
        if not category_cd or not self.code_repo.get_shop_code(category_cd):
            raise UndefinedCodeException(
                reason_code=ReasonCode.UNDEFINED_CODE_DETECTED,
                stage=self.NAME,
                entity_type="store",
                detail=f"category_cd is missing or invalid in CodeTable: {category_cd}"
            )

    def _load_map_and_shop(self, session: Session, store: Dict[str, Any], category_cd: str) -> str:
        map_id = session.execute(text(QUERY_UPSERT_MAP), {
            "name": store["name"],
            "category_cd": category_cd,
            "address_cd": store["address_cd"],
            "address_detail": store["address_detail"],
            "latitude": float(store.get("latitude", 0.0)),
            "longitude": float(store.get("longitude", 0.0))
        }).scalar()

        shop_id = session.execute(text(QUERY_UPSERT_SHOP), {
            "map_id": map_id,
            "shop_cd": store["shop_cd"],
            "rating": float(store.get("rating", 0.0))
        }).scalar()
        
        return str(shop_id), str(map_id)

    def _load_menus(self, session: Session, menus: List[Dict[str, Any]], shop_id: str):
        for menu in menus:
            session.execute(text(QUERY_INSERT_MENU), {
                "shop_id": int(shop_id),
                "name": menu["name"],
                "price": menu["price"]
            })

    def _load_images(self, session: Session, images: List[Any], shop_id: str):
        for img in images:
            img_url = img.get("url", "") if isinstance(img, dict) else img
            if img_url:
                session.execute(text(QUERY_INSERT_IMAGE), {
                    "image_url": img_url,
                    "table_name": "shop",
                    "table_id": int(shop_id)
                })

    def _load_crawling_and_reviews(self, session: Session, store: Dict[str, Any], reviews: List[Dict[str, Any]], map_id: str, category_cd: str):
        session.execute(text(QUERY_INSERT_CRAWLING), {
            "title": f"Crawl - {store['name']}",
            "content": store.get("description", ""),
            "article_url": store.get("canonical_url", ""),
            "map_id": int(map_id),
            "category_cd": category_cd,
            "author": "System",
            "keywords": "",
            "point": float(store.get("rating", 0.0))
        })

        for review in reviews:
            session.execute(text(QUERY_INSERT_CRAWLING), {
                "title": f"Review - {store['name']}",
                "content": review.get("content", ""),
                "article_url": store.get("canonical_url", ""),
                "map_id": int(map_id),
                "category_cd": category_cd,
                "author": review.get("author", "Anonymous"),
                "keywords": ",".join(review.get("keywords", [])),
                "point": float(review.get("rating", 0.0))
            })

    def execute(self, normalized_data: List[Dict[str, Any]], batch_id: str, category_cd: str, run_attempt: int = 1) -> List[Dict[str, Any]]:
        results = []
        loaded_count = 0
        with self.db.get_session() as session:
            for record in normalized_data:
                store = record.get("store", {})
                
                try:
                    # Design.md Rule: Stage 4 Load 직전 코드 테이블 참조 무결성 재검증
                    self._validate_required_codes(store, category_cd)
                    
                    # 1. Main Store Transaction
                    with session.begin_nested():
                        shop_id, map_id = self._load_map_and_shop(session, store, category_cd)
                    
                    # 2. Child Transactions
                    try:
                        with session.begin_nested():
                            self._load_menus(session, record.get("menus", []), shop_id)
                    except Exception as e:
                        self.logger.error(f"Menu partial failure for {store.get('name')}: {e}")
                        results.append({
                            "entity_id": store.get("entity_id", "unknown"),
                            "entity_type": "menu",
                            "status": "fail",
                            "reason_code": ReasonCode.DB_CONSTRAINT_VIOLATION.value,
                            "detail": str(e),
                            "data": record.get("menus", [])
                        })

                    try:
                        with session.begin_nested():
                            self._load_images(session, record.get("images", []), shop_id)
                    except Exception as e:
                        self.logger.error(f"Images partial failure for {store.get('name')}: {e}")
                        results.append({
                            "entity_id": store.get("entity_id", "unknown"),
                            "entity_type": "image",
                            "status": "fail",
                            "reason_code": ReasonCode.DB_CONSTRAINT_VIOLATION.value,
                            "detail": str(e),
                            "data": record.get("images", [])
                        })

                    try:
                        with session.begin_nested():
                            self._load_crawling_and_reviews(session, store, record.get("reviews", []), map_id, category_cd)
                    except Exception as e:
                        self.logger.error(f"Reviews partial failure for {store.get('name')}: {e}")
                        results.append({
                            "entity_id": store.get("entity_id", "unknown"),
                            "entity_type": "review",
                            "status": "fail",
                            "reason_code": ReasonCode.DB_CONSTRAINT_VIOLATION.value,
                            "detail": str(e),
                            "data": record.get("reviews", [])
                        })
                        
                    session.commit()
                    
                    loaded_count += 1
                    results.append({
                        "entity_id": store.get("entity_id", "unknown"),
                        "entity_type": "store",
                        "status": "success",
                        "data": record
                    })
                        
                except UndefinedCodeException as e:
                    session.rollback()
                    self.logger.warning(f"Load Policy Validation failed for {store.get('name')}: {str(e)}")
                    results.append({
                        "entity_id": store.get("entity_id", "unknown"),
                        "entity_type": "store",
                        "status": "fail",
                        "reason_code": e.reason_code.value,
                        "detail": e.detail,
                        "data": record
                    })
                except IntegrityError as e:
                    session.rollback()
                    self.logger.error(f"DB Constraint Integrity failed for {store.get('name')}: {str(e)}")
                    results.append({
                        "entity_id": store.get("entity_id", "unknown"),
                        "entity_type": "store",
                        "status": "fail",
                        "reason_code": ReasonCode.DB_CONSTRAINT_VIOLATION.value,
                        "detail": str(e),
                        "data": record
                    })
                except Exception as e:
                    session.rollback()
                    self.logger.error(f"DB Load failed critically for {store.get('name')}: {str(e)}")
                    results.append({
                        "entity_id": store.get("entity_id", "unknown"),
                        "entity_type": "store",
                        "status": "fail",
                        "reason_code": ReasonCode.UNKNOWN_ERROR.value,
                        "detail": str(e),
                        "data": record
                    })
                    
        self.logger.info(f"Loaded {loaded_count} stores with related data to DB.")
        return results
