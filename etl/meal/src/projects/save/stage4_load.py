import logging
from html import escape
from typing import Any, Dict, List

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.core.base_stage import BaseStage
from src.core.constants import (
    QUERY_FIND_MAP,
    QUERY_FIND_SHOP,
    QUERY_INSERT_MAP,
    QUERY_INSERT_CRAWLING,
    QUERY_INSERT_IMAGE,
    QUERY_INSERT_MENU,
    QUERY_INSERT_SHOP,
    QUERY_TOUCH_SHOP_CHECKED_AT,
    QUERY_UPDATE_MAP_COORDINATES,
    QUERY_UPDATE_SHOP_RATING,
    RESTAURANT_CATEGORY_CD,
    RESTAURANT_INFORMATION_CD,
    TABLE_NAME_CRAWLING,
)
from src.core.policy.exceptions import UndefinedCodeException
from src.core.policy.fail_record import build_fail_record
from src.core.policy.reason_code import ReasonCode
from src.core.repository.code_table_repository import CodeTableRepository
from src.core.repository.database import DatabaseManager


class Stage4Load(BaseStage):
    NAME = "load"
    CRAWLING_TITLE_MAX_LENGTH = 200
    CRAWLING_ARTICLE_URL_MAX_LENGTH = 500
    CRAWLING_AUTHOR_MAX_LENGTH = 100
    CRAWLING_KEYWORDS_MAX_LENGTH = 100
    IMAGE_URL_MAX_LENGTH = 500

    def __init__(self, db=None, code_repository: CodeTableRepository | None = None):
        super().__init__(self.NAME)
        self.db = db or DatabaseManager()
        self.code_repo = code_repository or CodeTableRepository()
        self.logger = logging.getLogger(self.__class__.__name__)

    def _validate_required_codes(self, store: Dict[str, Any], shop_cd: str):
        addr_cd = store.get("address_cd")
        store_shop_cd = store.get("shop_cd")

        if not addr_cd or addr_cd == "UNKNOWN" or not self.code_repo.get_address_info(addr_cd):
            raise UndefinedCodeException(
                reason_code=ReasonCode.UNDEFINED_CODE_DETECTED,
                stage=self.NAME,
                entity_type="store",
                detail=f"address_cd is missing, UNKNOWN, or invalid in CodeTable: {addr_cd}",
            )

        if not store_shop_cd or not self.code_repo.get_shop_code(store_shop_cd):
            raise UndefinedCodeException(
                reason_code=ReasonCode.UNDEFINED_CODE_DETECTED,
                stage=self.NAME,
                entity_type="store",
                detail=f"shop_cd is missing or invalid in CodeTable: {store_shop_cd}",
            )

        if not shop_cd or not self.code_repo.get_shop_code(shop_cd):
            raise UndefinedCodeException(
                reason_code=ReasonCode.UNDEFINED_CODE_DETECTED,
                stage=self.NAME,
                entity_type="store",
                detail=f"input shop_cd is missing or invalid in CodeTable: {shop_cd}",
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
            store = record.get("store", {})
            session.execute(text(QUERY_TOUCH_SHOP_CHECKED_AT), {
                "shop_id": int(shop_id),
                "title": f"Checked - {store.get('name', 'unknown')}",
                "content": store.get("description", ""),
                "article_url": store.get("canonical_url", ""),
                "category_cd": None,
                "information_cd": RESTAURANT_INFORMATION_CD,
                "author": "System",
                "keywords": "",
                "point": float(store.get("rating", 0.0)),
            })

    def _load_map_and_shop(self, session: Session, store: Dict[str, Any], record: Dict[str, Any], shop_cd: str) -> str:
        map_params = {
            "name": store["name"],
            "category_cd": RESTAURANT_CATEGORY_CD,
            "address_cd": store["address_cd"],
            "address_detail": store["address_detail"],
            "latitude": float(store.get("latitude", 0.0)),
            "longitude": float(store.get("longitude", 0.0)),
        }
        map_id = session.execute(text(QUERY_FIND_MAP), map_params).scalar()
        if map_id:
            session.execute(text(QUERY_UPDATE_MAP_COORDINATES), {**map_params, "map_id": map_id})
        else:
            map_id = session.execute(text(QUERY_INSERT_MAP), map_params).scalar()

        shop_params = {
            "map_id": map_id,
            "shop_cd": store["shop_cd"],
            "rating": float(store.get("rating", 0.0)),
        }
        shop_id = session.execute(text(QUERY_FIND_SHOP), shop_params).scalar()
        if shop_id:
            session.execute(text(QUERY_UPDATE_SHOP_RATING), {**shop_params, "shop_id": shop_id})
        else:
            shop_id = session.execute(text(QUERY_INSERT_SHOP), shop_params).scalar()

        return str(shop_id), str(map_id)

    def _resolve_store_identity(
        self,
        session: Session,
        store: Dict[str, Any],
        record: Dict[str, Any],
        shop_cd: str,
        change_plan: Dict[str, bool],
    ) -> tuple[str, str]:
        if not change_plan["store"] and record.get("existing_store_id") and record.get("existing_map_id"):
            return str(record["existing_store_id"]), str(record["existing_map_id"])

        return self._load_map_and_shop(session, store, record, shop_cd)

    def _load_menus(self, session: Session, menus: List[Dict[str, Any]], shop_id: str):
        for menu in menus:
            session.execute(text(QUERY_INSERT_MENU), {
                "shop_id": int(shop_id),
                "name": menu["name"],
                "price": menu["price"],
            })

    def _resolve_table_code(self, table_name: str) -> str:
        table_cd = self.code_repo.get_table_code(table_name)
        if not table_cd:
            raise UndefinedCodeException(
                reason_code=ReasonCode.UNDEFINED_CODE_DETECTED,
                stage=self.NAME,
                entity_type="image",
                detail=f"table_cd is missing or invalid in CodeTable: {table_name}",
            )
        return table_cd

    def _load_images(
        self,
        session: Session,
        images: List[Any],
        source_table_name: str,
        source_id: str,
    ):
        if source_id is None or str(source_id).strip() == "":
            raise ValueError("image source_id is required")

        table_cd = self._resolve_table_code(source_table_name)
        table_id = int(source_id)

        for img in images:
            img_url = img.get("url", "") if isinstance(img, dict) else img
            if img_url:
                session.execute(text(QUERY_INSERT_IMAGE), {
                    "image_url": self._build_image_tag(img_url),
                    "table_cd": table_cd,
                    "table_id": table_id,
                })

    def _limit_text(self, value: Any, max_length: int) -> str:
        if value is None:
            return ""
        return str(value)[:max_length]

    def _join_keywords(self, keywords: Any) -> str:
        if not keywords:
            return ""
        if isinstance(keywords, list):
            text = ",".join(str(keyword) for keyword in keywords)
        else:
            text = str(keywords)
        return self._limit_text(text, self.CRAWLING_KEYWORDS_MAX_LENGTH)

    def _build_anchor_tag(self, url: Any, label: Any) -> str:
        raw_url = str(url or "").strip()
        if not raw_url:
            return ""

        escaped_url = escape(raw_url, quote=True)
        prefix = f'<a href="{escaped_url}">'
        suffix = "</a>"
        label_budget = self.CRAWLING_ARTICLE_URL_MAX_LENGTH - len(prefix) - len(suffix)
        if label_budget <= 0:
            return self._limit_text(raw_url, self.CRAWLING_ARTICLE_URL_MAX_LENGTH)

        escaped_label = escape(str(label or raw_url).strip(), quote=False)
        visible_label = self._limit_text(escaped_label, label_budget)
        return f"{prefix}{visible_label}</a>"

    def _build_image_tag(self, image_url: Any, alt_text: Any = "식당 이미지") -> str:
        raw_url = str(image_url or "").strip()
        if not raw_url:
            return ""

        escaped_url = escape(raw_url, quote=True)
        prefix = f'<img src="{escaped_url}" alt="'
        suffix = '"/>'
        alt_budget = self.IMAGE_URL_MAX_LENGTH - len(prefix) - len(suffix)
        if alt_budget <= 0:
            return self._limit_text(raw_url, self.IMAGE_URL_MAX_LENGTH)

        escaped_alt = escape(str(alt_text or "식당 이미지").strip(), quote=True)
        visible_alt = self._limit_text(escaped_alt, alt_budget)
        return f"{prefix}{visible_alt}{suffix}"

    def _load_crawling_and_reviews(
        self,
        session: Session,
        store: Dict[str, Any],
        reviews: List[Dict[str, Any]],
        map_id: str,
        shop_cd: str,
    ):
        store_crawling_id = session.execute(text(QUERY_INSERT_CRAWLING), {
            "title": self._limit_text(f"Crawl - {store['name']}", self.CRAWLING_TITLE_MAX_LENGTH),
            "content": store.get("description", ""),
            "article_url": self._build_anchor_tag(store.get("canonical_url", ""), store.get("name", "")),
            "map_id": int(map_id),
            "category_cd": RESTAURANT_CATEGORY_CD,
            "information_cd": RESTAURANT_INFORMATION_CD,
            "shop_cd": shop_cd,
            "author": "System",
            "keywords": "",
            "point": float(store.get("rating", 0.0)),
        }).scalar()

        for review in reviews:
            session.execute(text(QUERY_INSERT_CRAWLING), {
                "title": self._limit_text(f"Review - {store['name']}", self.CRAWLING_TITLE_MAX_LENGTH),
                "content": review.get("content", ""),
                "article_url": self._build_anchor_tag(store.get("canonical_url", ""), store.get("name", "")),
                "map_id": int(map_id),
                "category_cd": RESTAURANT_CATEGORY_CD,
                "information_cd": RESTAURANT_INFORMATION_CD,
                "shop_cd": shop_cd,
                "author": self._limit_text(review.get("author", "Anonymous"), self.CRAWLING_AUTHOR_MAX_LENGTH),
                "keywords": self._join_keywords(review.get("keywords", [])),
                "point": float(review.get("rating", 0.0)),
            })

        return str(store_crawling_id) if store_crawling_id is not None else None

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
        shop_cd = category_cd
        results = []
        loaded_count = 0
        with self.db.get_session() as session:
            for record in normalized_data:
                store = record.get("store", {})
                change_plan = self._build_change_plan(record)

                try:
                    self._validate_required_codes(store, shop_cd)

                    if change_plan["touch_only"]:
                        with session.begin_nested():
                            self._touch_last_checked_at(session, record)
                        session.commit()
                        results.append({
                            "batch_id": batch_id,
                            "run_attempt": run_attempt,
                            "stage": self.NAME,
                            "category_cd": RESTAURANT_CATEGORY_CD,
                            "shop_cd": shop_cd,
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
                            shop_cd,
                            change_plan,
                        )

                    if change_plan["menu"]:
                        try:
                            with session.begin_nested():
                                self._load_menus(session, record.get("menus", []), shop_id)
                        except Exception as e:
                            self.logger.error(f"Menu partial failure for {store.get('name')}: {e}")
                            self._record_partial_failure(results, store, "menu", e, record.get("menus", []), batch_id, run_attempt)

                    crawling_source_id = None
                    if change_plan["image"] or change_plan["review"]:
                        try:
                            with session.begin_nested():
                                crawling_source_id = self._load_crawling_and_reviews(
                                    session,
                                    store,
                                    record.get("reviews", []) if change_plan["review"] else [],
                                    map_id,
                                    shop_cd,
                                )
                        except Exception as e:
                            entity_type = "review" if change_plan["review"] else "image"
                            failure_data = record.get("reviews", []) if change_plan["review"] else record.get("images", [])
                            self.logger.error(f"Crawling source partial failure for {store.get('name')}: {e}")
                            self._record_partial_failure(results, store, entity_type, e, failure_data, batch_id, run_attempt)

                    if change_plan["image"]:
                        try:
                            with session.begin_nested():
                                self._load_images(
                                    session,
                                    record.get("images", []),
                                    TABLE_NAME_CRAWLING,
                                    crawling_source_id,
                                )
                        except Exception as e:
                            self.logger.error(f"Images partial failure for {store.get('name')}: {e}")
                            self._record_partial_failure(results, store, "image", e, record.get("images", []), batch_id, run_attempt)

                    session.commit()
                    loaded_count += 1
                    status = "partial_failure" if any(
                        r.get("status") == "fail" and r.get("entity_id") == store.get("entity_id", "unknown")
                        for r in results
                    ) else "success"
                    results.append({
                        "batch_id": batch_id,
                        "run_attempt": run_attempt,
                        "stage": self.NAME,
                        "category_cd": RESTAURANT_CATEGORY_CD,
                        "shop_cd": shop_cd,
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
