import logging
from typing import Any, Dict, List

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.core.base_stage import BaseStage
from src.core.constants import (
    QUERY_INSERT_CRAWLING,
    QUERY_INSERT_IMAGE,
    QUERY_INSERT_MENU,
    QUERY_TOUCH_SHOP_CHECKED_AT,
    QUERY_UPSERT_MAP,
    QUERY_UPSERT_SHOP,
)
from src.core.policy.exceptions import UndefinedCodeException
from src.core.policy.fail_record import build_fail_record
from src.core.policy.reason_code import ReasonCode
from src.core.repository.code_table_repository import CodeTableRepository
from src.core.repository.database import DatabaseManager


class Stage4Load(BaseStage):
    NAME = "load"

    def __init__(self, db=None, code_repository: CodeTableRepository | None = None):
        super().__init__(self.NAME)
        self.db = db or DatabaseManager()
        self.code_repo = code_repository or CodeTableRepository()
        self.logger = logging.getLogger(self.__class__.__name__)

    def _validate_required_codes(self, store: Dict[str, Any], category_cd: str):
        addr_cd = store.get("address_cd")
        shop_cd = store.get("shop_cd")

        if not addr_cd or addr_cd == "UNKNOWN" or not self.code_repo.get_address_info(addr_cd):
            raise UndefinedCodeException(
                reason_code=ReasonCode.UNDEFINED_CODE_DETECTED,
                stage=self.NAME,
                entity_type="store",
                detail=f"address_cd is missing, UNKNOWN, or invalid in CodeTable: {addr_cd}",
            )

        if not shop_cd or not self.code_repo.get_shop_code(shop_cd):
            raise UndefinedCodeException(
                reason_code=ReasonCode.UNDEFINED_CODE_DETECTED,
                stage=self.NAME,
                entity_type="store",
                detail=f"shop_cd is missing or invalid in CodeTable: {shop_cd}",
            )

        if not category_cd or not self.code_repo.get_shop_code(category_cd):
            raise UndefinedCodeException(
                reason_code=ReasonCode.UNDEFINED_CODE_DETECTED,
                stage=self.NAME,
                entity_type="store",
                detail=f"category_cd is missing or invalid in CodeTable: {category_cd}",
            )

    def _build_change_plan(self, record: Dict[str, Any]) -> Dict[str, bool]:
        if record.get("is_changed") is False:
            return {
                "store": False,
                "menu": False,
                "review": False,
                "image": False,
                "touch_only": True,
            }

        return {
            "store": record.get("store_changed", True),
            "menu": record.get("menu_changed", True),
            "review": record.get("review_changed", True),
            "image": record.get("image_changed", True),
            "touch_only": False,
        }

    def _touch_last_checked_at(self, session: Session, record: Dict[str, Any]) -> None:
        shop_id = record.get("existing_store_id") or record.get("store_id")
        if shop_id:
            session.execute(text(QUERY_TOUCH_SHOP_CHECKED_AT), {"shop_id": int(shop_id)})

    def _load_map_and_shop(self, session: Session, store: Dict[str, Any], record: Dict[str, Any], category_cd: str) -> str:
        map_id = session.execute(text(QUERY_UPSERT_MAP), {
            "name": store["name"],
            "category_cd": category_cd,
            "address_cd": store["address_cd"],
            "address_detail": store["address_detail"],
            "latitude": float(store.get("latitude", 0.0)),
            "longitude": float(store.get("longitude", 0.0)),
        }).scalar()

        shop_id = session.execute(text(QUERY_UPSERT_SHOP), {
            "map_id": map_id,
            "shop_cd": store["shop_cd"],
            "rating": float(store.get("rating", 0.0)),
            "store_content_hash": record.get("store_content_hash"),
            "menu_content_hash": record.get("menu_content_hash"),
            "review_content_hash": record.get("review_content_hash"),
            "image_content_hash": record.get("image_content_hash"),
        }).scalar()

        return str(shop_id), str(map_id)

    def _resolve_store_identity(
        self,
        session: Session,
        store: Dict[str, Any],
        record: Dict[str, Any],
        category_cd: str,
        change_plan: Dict[str, bool],
    ) -> tuple[str, str]:
        if not change_plan["store"] and record.get("existing_store_id") and record.get("existing_map_id"):
            return str(record["existing_store_id"]), str(record["existing_map_id"])

        return self._load_map_and_shop(session, store, record, category_cd)

    def _load_menus(self, session: Session, menus: List[Dict[str, Any]], shop_id: str):
        for menu in menus:
            session.execute(text(QUERY_INSERT_MENU), {
                "shop_id": int(shop_id),
                "name": menu["name"],
                "price": menu["price"],
            })

    def _load_images(self, session: Session, images: List[Any], shop_id: str):
        for img in images:
            img_url = img.get("url", "") if isinstance(img, dict) else img
            if img_url:
                session.execute(text(QUERY_INSERT_IMAGE), {
                    "image_url": img_url,
                    "table_name": "shop",
                    "table_id": int(shop_id),
                })

    def _load_crawling_and_reviews(
        self,
        session: Session,
        store: Dict[str, Any],
        reviews: List[Dict[str, Any]],
        map_id: str,
        category_cd: str,
    ):
        session.execute(text(QUERY_INSERT_CRAWLING), {
            "title": f"Crawl - {store['name']}",
            "content": store.get("description", ""),
            "article_url": store.get("canonical_url", ""),
            "map_id": int(map_id),
            "category_cd": category_cd,
            "author": "System",
            "keywords": "",
            "point": float(store.get("rating", 0.0)),
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
                "point": float(review.get("rating", 0.0)),
            })

    def _record_partial_failure(
        self,
        results: list,
        store: dict,
        entity_type: str,
        detail: Exception,
        data: Any,
        batch_id: str,
        run_attempt: int,
    ):
        results.append(build_fail_record(
            batch_id=batch_id,
            run_attempt=run_attempt,
            stage=self.NAME,
            entity_type=entity_type,
            entity_id=store.get("entity_id", "unknown"),
            entity_ref=store.get("entity_ref", {}),
            reason_code=ReasonCode.DB_CONSTRAINT_VIOLATION,
            detail=str(detail),
            data=data,
        ))

    def execute(
        self,
        normalized_data: List[Dict[str, Any]],
        batch_id: str,
        category_cd: str,
        run_attempt: int = 1,
    ) -> List[Dict[str, Any]]:
        results = []
        loaded_count = 0
        with self.db.get_session() as session:
            for record in normalized_data:
                store = record.get("store", {})
                change_plan = self._build_change_plan(record)

                try:
                    self._validate_required_codes(store, category_cd)

                    if change_plan["touch_only"]:
                        with session.begin_nested():
                            self._touch_last_checked_at(session, record)
                        session.commit()
                        results.append({
                            "entity_id": store.get("entity_id", "unknown"),
                            "entity_type": "store",
                            "status": "success",
                            "action": "checked_only",
                            "data": record,
                        })
                        continue

                    with session.begin_nested():
                        shop_id, map_id = self._resolve_store_identity(
                            session,
                            store,
                            record,
                            category_cd,
                            change_plan,
                        )

                    if change_plan["menu"]:
                        try:
                            with session.begin_nested():
                                self._load_menus(session, record.get("menus", []), shop_id)
                        except Exception as e:
                            self.logger.error(f"Menu partial failure for {store.get('name')}: {e}")
                            self._record_partial_failure(results, store, "menu", e, record.get("menus", []), batch_id, run_attempt)

                    if change_plan["image"]:
                        try:
                            with session.begin_nested():
                                self._load_images(session, record.get("images", []), shop_id)
                        except Exception as e:
                            self.logger.error(f"Images partial failure for {store.get('name')}: {e}")
                            self._record_partial_failure(results, store, "image", e, record.get("images", []), batch_id, run_attempt)

                    if change_plan["review"]:
                        try:
                            with session.begin_nested():
                                self._load_crawling_and_reviews(
                                    session,
                                    store,
                                    record.get("reviews", []),
                                    map_id,
                                    category_cd,
                                )
                        except Exception as e:
                            self.logger.error(f"Reviews partial failure for {store.get('name')}: {e}")
                            self._record_partial_failure(results, store, "review", e, record.get("reviews", []), batch_id, run_attempt)

                    session.commit()
                    loaded_count += 1
                    status = "partial_failure" if any(
                        r.get("status") == "fail" and r.get("entity_id") == store.get("entity_id", "unknown")
                        for r in results
                    ) else "success"
                    results.append({
                        "entity_id": store.get("entity_id", "unknown"),
                        "entity_type": "store",
                        "status": status,
                        "data": record,
                    })

                except UndefinedCodeException as e:
                    session.rollback()
                    self.logger.warning(f"Load Policy Validation failed for {store.get('name')}: {str(e)}")
                    results.append(build_fail_record(
                        batch_id=batch_id,
                        run_attempt=run_attempt,
                        stage=self.NAME,
                        entity_type="store",
                        entity_id=store.get("entity_id", "unknown"),
                        entity_ref=store.get("entity_ref", {}),
                        reason_code=e.reason_code,
                        detail=e.detail,
                        data=record,
                    ))
                except IntegrityError as e:
                    session.rollback()
                    self.logger.error(f"DB Constraint Integrity failed for {store.get('name')}: {str(e)}")
                    results.append(build_fail_record(
                        batch_id=batch_id,
                        run_attempt=run_attempt,
                        stage=self.NAME,
                        entity_type="store",
                        entity_id=store.get("entity_id", "unknown"),
                        entity_ref=store.get("entity_ref", {}),
                        reason_code=ReasonCode.DB_CONSTRAINT_VIOLATION,
                        detail=str(e),
                        data=record,
                    ))
                except Exception as e:
                    session.rollback()
                    self.logger.error(f"DB Load failed critically for {store.get('name')}: {str(e)}")
                    results.append(build_fail_record(
                        batch_id=batch_id,
                        run_attempt=run_attempt,
                        stage=self.NAME,
                        entity_type="store",
                        entity_id=store.get("entity_id", "unknown"),
                        entity_ref=store.get("entity_ref", {}),
                        reason_code=ReasonCode.UNKNOWN_ERROR,
                        detail=str(e),
                        data=record,
                    ))

        self.logger.info(f"Loaded {loaded_count} stores with related data to DB.")
        if hasattr(self.code_repo, "clear_cache"):
            self.code_repo.clear_cache()
        return results
