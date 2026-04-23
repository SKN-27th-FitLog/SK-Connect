# 상수 정리 및 표준화 (Constants Cleanup) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `pipeline_constants.py`의 미사용 상수를 제거하고, 하드코딩된 문자열들을 상수로 대체하여 관리 효율성을 높임.

**Architecture:** `Enum` 기반 상수를 정의하고 외부 모듈(Repository, Collector, Orchestrator)에서 이를 참조하도록 리팩토링.

**Tech Stack:** Python 3.12, Enum

---

### Task 1: `pipeline_constants.py` 정리 및 신규 상수 추가

**Files:**
- Modify: `src/core/constants/pipeline_constants.py`

- [ ] **Step 1: `pipeline_constants.py` 내용 수정**
    기존 미사용 클래스들을 삭제하고 `PlatformSource`를 추가합니다.
    ```python
    from enum import Enum
    from typing import Final

    class CrawlerThread(Enum):
        """크롤링 스레드 구분"""
        SHOP: Final[str] = "shop"
        REVIEW: Final[str] = "review"

    class LoadStatus(Enum):
        """결과 상태 코드"""
        SUCCESS: Final[str] = "success"
        FAIL: Final[str] = "fail"

    class PlatformSource(Enum):
        """수집 플랫폼 코드"""
        DININGCODE: Final[str] = "DCODE"
    ```

- [ ] **Step 2: 문법 오류 여부 확인**
    `python -m py_compile src/core/constants/pipeline_constants.py` 실행하여 오류 없는지 확인.

---

### Task 2: `StoreRepository.py` 리팩토링

**Files:**
- Modify: `src/db/repositories/store_repository.py`

- [ ] **Step 1: 상수 임포트 및 적용**
    `shop_cd`와 `INSERT_CRAWLING`의 `"review"`를 상수로 교체합니다.
    ```python
    # 상단 임포트 추가
    from ...core.constants.pipeline_constants import CrawlerThread, PlatformSource

    # save_store 메서드 내 수정
    @db_transaction
    def save_store(self, conn, cur, store_data: dict) -> int:
        category_cd = (store_data.get('category_cd') or 'SC06')[:6]
        address_cd = (store_data.get('address_cd') or '11000')[:6]
        shop_cd = PlatformSource.DININGCODE.value # "DCODE" 대체

        # ... 중간 생략 ...

        # 4. Crawling (Review) 테이블 적재
        reviews = store_data.get('reviews', [])
        for rev in reviews:
            cur.execute(StoreQueries.INSERT_CRAWLING, (
                map_id,
                rev.get('title', '리뷰'),
                rev.get('content', ''),
                CrawlerThread.REVIEW.value, # "review" 대체
                '', 
                rev.get('point', 0.0),
                rev.get('author', 'anonymous'),
                category_cd
            ))
    ```

- [ ] **Step 2: 코드 확인**
    수정된 위치의 코드가 올바르게 연결되었는지 확인.

---

### Task 3: `HttpCollector.py` 및 `OrchestratorV4.py` 리팩토링

**Files:**
- Modify: `src/services/collectors/http_collector.py`
- Modify: `src/pipeline/orchestrator_v4.py`

- [ ] **Step 1: `HttpCollector.py` 수정**
    상수 적용:
    ```python
    from ...core.constants.pipeline_constants import LoadStatus

    # collect 메서드 반환값 수정
    return {
        "status": LoadStatus.SUCCESS.value,
        "raw_content": response.text,
        # ...
    }
    # 예외 처리 시
    return {
        "status": LoadStatus.FAIL.value,
        "reason_code": "NETWORK_ERROR",
        # ...
    }
    ```

- [ ] **Step 2: `OrchestratorV4.py` 수정**
    상수 적용:
    ```python
    from ..core.constants.pipeline_constants import LoadStatus

    # run_daily_batch 메서드 내 조건문 수정
    if raw["status"] == LoadStatus.FAIL.value:
        # ...
    ```

---

### Task 4: 통합 테스트 및 검증

- [ ] **Step 1: 전체 파이프라인 실행 확인**
    `python main.py --category SC02 --goal 1` 실행하여 정상 적재되는지 확인.

- [ ] **Step 2: 최종 커밋**
    ```bash
    git add src/core/constants/pipeline_constants.py src/db/repositories/store_repository.py src/services/collectors/http_collector.py src/pipeline/orchestrator_v4.py
    git commit -m "refactor: standardize constants and cleanup unused codes"
    ```
