# ETL Core Architecture Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Resolve critical high-priority architecture violations (H1, H2, H3, H5, H6) and strictly enforce `Design.md` principles (Domain Exception usage, Enum-based reason codes, Single Responsibility mapping, Partial Failure transactions, Fail Ledger Routing, and Code Table Integrity).

**Architecture:** 
1. `DatabaseManager` eager loading deferred to property access.
2. `Stage3ValidationNormalization` encapsulation boundary preserved.
3. `exceptions.py` and `reason_code.py` updated to support `UndefinedCodeException` and literal `.value` mappings.
4. `Stage4Load` completely refactored to:
   - Extract logic into single-responsibility methods.
   - Use `UndefinedCodeException`, `ReasonCode` explicitly.
   - Re-verify Code Table Integrity immediately before loading against `CodeTableRepository`.
   - Separate transaction boundaries for `store` vs `menu/review/images`.
   - Propagate child failures directly to the `fail` ledger list.
   - Inject dynamic `category_cd` to remove hardcoding.

**Tech Stack:** Python, SQLAlchemy

---

### Task 1: Fix Database Eager Initialization (H6)

The current `database.py` initializes the `create_engine` eagerly at the module level when imported.

**Files:**
- Modify: `src/core/repository/database.py`

- [ ] **Step 1: Defere engine creation using properties**

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
from typing import Generator
from src.core.config import settings
import logging

logger = logging.getLogger(__name__)

class DatabaseManager:
    """
    DB 연결 및 세션을 관리하는 클래스.
    설계안 5-3 (global mutable state 금지) 원칙 준수.
    """
    def __init__(self, db_url: str = None):
        self._db_url = db_url
        self._engine = None
        self._SessionLocal = None

    @property
    def engine(self):
        if self._engine is None:
            url = self._db_url or settings.database_url
            self._engine = create_engine(
                url,
                pool_size=5,
                max_overflow=10,
                pool_pre_ping=True,
                echo=False
            )
        return self._engine

    @property
    def SessionLocal(self):
        if self._SessionLocal is None:
            self._SessionLocal = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=self.engine
            )
        return self._SessionLocal

    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        session = self.SessionLocal()
        try:
            yield session
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

db_manager = DatabaseManager()
```

- [ ] **Step 2: Commit Task 1**

```bash
git add src/core/repository/database.py
git commit -m "fix: defer database engine creation until accessed (H6)"
```

---

### Task 2: Resolve Encapsulation Violation (H5)

`Stage3ValidationNormalization` directly accesses `_address_cache`.

**Files:**
- Modify: `src/core/repository/code_table_repository.py`
- Modify: `src/projects/process/stage3_validation_normalization.py`

- [ ] **Step 1: Expose public cache method**

Modify `src/core/repository/code_table_repository.py`. Add this method inside `CodeTableRepository`:

```python
    def get_all_addresses(self) -> Dict[str, Dict[str, Any]]:
        """전체 주소 정보 딕셔너리 반환"""
        if not self._is_loaded:
            self.preload()
        return self._address_cache
```

- [ ] **Step 2: Refactor caller in Stage 3**

Modify `src/projects/process/stage3_validation_normalization.py` lines 29-38:

```python
        best_match_cd = "UNKNOWN"
        detail = full_address
        addresses = self.code_repo.get_all_addresses()
        sorted_addresses = sorted(addresses.items(), key=lambda x: len(x[0]), reverse=True)
        for addr_key, info in sorted_addresses:
            if full_address.replace(" ", "").startswith(addr_key.replace(" ", "")):
                best_match_cd = info['address_cd']
                detail = full_address.replace(addr_key, "").strip()
                break
                
        return best_match_cd, detail
```

- [ ] **Step 3: Commit Task 2**

```bash
git add src/core/repository/code_table_repository.py src/projects/process/stage3_validation_normalization.py
git commit -m "fix: expose public address cache access (H5)"
```

---

### Task 3: Enum Value Updates and Exception Classes

Ensure that `ReasonCode` maps directly to explicit string values instead of generic `auto()` integers for stable `.value` usage, and create `UndefinedCodeException`.

**Files:**
- Modify: `src/core/policy/reason_code.py`
- Modify: `src/core/policy/exceptions.py`

- [ ] **Step 1: Convert ReasonCode values to explicit strings**

Modify `src/core/policy/reason_code.py`:

```python
from enum import Enum

class ReasonCode(Enum):
    """
    ETL 파이프라인 전반에서 발생하는 실패의 원인을 정의하는 Enum.
    """
    NETWORK_ERROR = "NETWORK_ERROR"
    PROXY_ERROR = "PROXY_ERROR"
    TIMEOUT = "TIMEOUT"
    SELECTOR_MISMATCH = "SELECTOR_MISMATCH"
    BOT_DETECTED = "BOT_DETECTED"
    NOT_FOUND = "NOT_FOUND"      
    INVALID_URL = "INVALID_URL"
    INVALID_DATA_FORMAT = "INVALID_DATA_FORMAT"
    MISSING_REQUIRED_FIELD = "MISSING_REQUIRED_FIELD"
    NOT_RESTAURANT_ENTITY = "NOT_RESTAURANT_ENTITY" 
    CONFLICTING_DEDUP_SIGNALS = "CONFLICTING_DEDUP_SIGNALS" 
    DB_CONNECTION_ERROR = "DB_CONNECTION_ERROR"
    DB_CONSTRAINT_VIOLATION = "DB_CONSTRAINT_VIOLATION"
    UNDEFINED_CODE_DETECTED = "UNDEFINED_CODE_DETECTED" 
    UNKNOWN_ERROR = "UNKNOWN_ERROR"
    INTERNAL_PIPELINE_ERROR = "INTERNAL_PIPELINE_ERROR"

    def __str__(self):
        return self.value
```

- [ ] **Step 2: Add UndefinedCodeException**

Modify `src/core/policy/exceptions.py`. Add the following class:

```python
class UndefinedCodeException(BasePipelineException):
    """지정되지 않은 식별 불가 코드(예: UNKNOWN 주소) 또는 참조 무결성 위반 시 예외"""
    pass
```

- [ ] **Step 3: Commit Task 3**

```bash
git add src/core/policy/reason_code.py src/core/policy/exceptions.py
git commit -m "feat: use string values for ReasonCode and add UndefinedCodeException"
```

---

### Task 4: Refactor Stage 4 Load Policy, Transactions, and Code Table Integrity

Refactor `Stage4Load` to use explicit Helper methods. Re-verify Code Table references against `CodeTableRepository` to catch undefined states strictly before DB insertion. Route child failures directly to the return array.

**Files:**
- Modify: `src/projects/save/stage4_load.py`

- [ ] **Step 1: Re-write Stage4Load**

Overwrite `src/projects/save/stage4_load.py`:

```python
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

    def execute(self, normalized_data: List[Dict[str, Any]], batch_id: str, category_cd: str) -> List[Dict[str, Any]]:
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
```

- [ ] **Step 2: Commit Task 4**

```bash
git add src/projects/save/stage4_load.py
git commit -m "refactor: enforce CodeTable integrity pre-validation via CodeTableRepository in load stage as per Design.md sec 17"
```
