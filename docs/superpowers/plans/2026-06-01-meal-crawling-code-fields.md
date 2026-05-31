# Meal Crawling Code Fields Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `etl/meal` Stage 4 DB 적재 시 `crawling.information_cd=IC01`과 `crawling.shop_cd=SCxx`가 store 확인 row와 review row에 함께 저장되도록 한다.

**Architecture:** 변경 범위는 `etl/meal`의 Stage 4 Load와 SQL 상수에만 둔다. `crawling` 적재 SQL이 코드 필드를 직접 저장하고, Stage 4는 이미 검증된 입력 `shop_cd`를 `crawling` row까지 전달한다. `analysis` 보정 로직, DB 스키마, `post_analysis`, `postmake_pipeline`은 변경하지 않는다.

**Tech Stack:** Python, SQLAlchemy text query, PostgreSQL, pytest.

---

## Scope

포함한다.

- `etl/meal/src/core/constants.py`
  - `RESTAURANT_INFORMATION_CD = "IC01"` 상수 추가
  - `QUERY_INSERT_CRAWLING`에 `information_cd`, `shop_cd` 저장 추가
  - `QUERY_TOUCH_SHOP_CHECKED_AT`에 `information_cd`, `shop_cd` 저장 추가
- `etl/meal/src/projects/save/stage4_load.py`
  - `_touch_last_checked_at`에서 `information_cd=IC01` 전달
  - `_load_crawling_and_reviews`가 실제 입력 `shop_cd`를 받아 store/review crawling row에 전달
  - `execute()`에서 `_load_crawling_and_reviews(..., shop_cd)`를 넘기도록 수정
- `etl/meal/tests/test_stage4_backend_category_contract.py`
  - store/review/touch crawling row의 코드 필드 계약 테스트 추가

포함하지 않는다.

- DB 스키마 변경
- 기존 로컬 DB backfill SQL
- `analysis` 테이블 보정 로직 변경
- `ai/post_analysis`, `ai/postmake_pipeline` 변경
- IT 뉴스 `etl/it_news` 변경

---

### Task 1: Define Failing Stage 4 Contract Tests

**Files:**
- Modify: `etl/meal/tests/test_stage4_backend_category_contract.py`

- [ ] **Step 1: Update imports**

`RESTAURANT_INFORMATION_CD`를 테스트에서 import한다. 아직 상수가 없으므로 이 단계 이후 테스트는 실패해야 한다.

```python
from src.core.constants import RESTAURANT_CATEGORY_CD, RESTAURANT_INFORMATION_CD
from src.projects.save.stage4_load import Stage4Load
```

- [ ] **Step 2: Replace the existing crawling category test with code-field assertions**

기존 `test_load_crawling_and_reviews_writes_ca_category_to_crawling`를 아래 내용으로 교체한다.

```python
def test_load_crawling_and_reviews_writes_restaurant_codes_to_crawling():
    stage = Stage4Load(db=object(), code_repository=object())
    session = RecordingSession()
    store = {
        "name": "테스트 식당",
        "description": "설명",
        "canonical_url": "https://example.com/store",
        "rating": 4.5,
    }
    reviews = [{"content": "좋아요", "author": "tester", "keywords": ["친절"], "rating": 5}]

    stage._load_crawling_and_reviews(session, store, reviews, map_id="10", shop_cd="SC01")

    store_params = session.params[0]
    review_params = session.params[1]
    assert store_params["category_cd"] == RESTAURANT_CATEGORY_CD
    assert store_params["information_cd"] == RESTAURANT_INFORMATION_CD
    assert store_params["shop_cd"] == "SC01"
    assert review_params["category_cd"] == RESTAURANT_CATEGORY_CD
    assert review_params["information_cd"] == RESTAURANT_INFORMATION_CD
    assert review_params["shop_cd"] == "SC01"
```

- [ ] **Step 3: Update direct private-method callers to the new argument name**

같은 파일에서 `_load_crawling_and_reviews(..., category_cd="SC01")` 호출을 모두 `_load_crawling_and_reviews(..., shop_cd="SC01")`로 바꾼다.

```python
stage._load_crawling_and_reviews(session, store, [], map_id="10", shop_cd="SC01")
```

- [ ] **Step 4: Add touch-only SQL contract test**

`QUERY_TOUCH_SHOP_CHECKED_AT`는 `shop_id`로 `shop`을 조회하므로 `shop_cd`는 SQL에서 `s.shop_cd`를 저장해야 한다. 테스트 파일 하단에 아래 테스트를 추가한다.

```python
def test_touch_shop_checked_at_writes_restaurant_codes_to_crawling():
    from src.core.constants import QUERY_TOUCH_SHOP_CHECKED_AT

    assert "information_cd" in QUERY_TOUCH_SHOP_CHECKED_AT
    assert "shop_cd" in QUERY_TOUCH_SHOP_CHECKED_AT
    assert ":information_cd" in QUERY_TOUCH_SHOP_CHECKED_AT
    assert "s.shop_cd" in QUERY_TOUCH_SHOP_CHECKED_AT
```

- [ ] **Step 5: Run focused test and verify RED**

Run from `C:\dev\Project\SK-Connect`:

```powershell
$env:PYTHONPATH='C:\dev\Project\SK-Connect\etl\meal'
C:\Python314\python.exe -m pytest etl\meal\tests\test_stage4_backend_category_contract.py -v
```

Expected: FAIL because `RESTAURANT_INFORMATION_CD` does not exist and `_load_crawling_and_reviews` does not accept `shop_cd`.

---

### Task 2: Add SQL Constants And Crawling Code Columns

**Files:**
- Modify: `etl/meal/src/core/constants.py`

- [ ] **Step 1: Add restaurant information code constant**

Add this next to `RESTAURANT_CATEGORY_CD`.

```python
RESTAURANT_CATEGORY_CD = "CA01"
RESTAURANT_INFORMATION_CD = "IC01"
SHOP_CODE_PREFIX = "SC"
TABLE_NAME_CRAWLING = "crawling"
```

- [ ] **Step 2: Update `QUERY_TOUCH_SHOP_CHECKED_AT`**

Replace the query with this version.

```python
QUERY_TOUCH_SHOP_CHECKED_AT = """
    INSERT INTO crawling (
        title, content, article_url, map_id, category_cd,
        information_cd, shop_cd, author, keywords, point, created_at
    )
    SELECT
        :title,
        :content,
        :article_url,
        s.map_id,
        COALESCE(:category_cd, m.category_cd),
        :information_cd,
        s.shop_cd,
        :author,
        :keywords,
        :point,
        NOW()
    FROM shop s
    JOIN maps m ON m.map_id = s.map_id
    WHERE s.shop_id = :shop_id
    RETURNING crawling_id
"""
```

- [ ] **Step 3: Update `QUERY_INSERT_CRAWLING` insert columns and values**

Replace only the `inserted AS (...)` CTE with this version.

```python
    inserted AS (
        INSERT INTO crawling (
            title, content, article_url, map_id, category_cd,
            information_cd, shop_cd, author, keywords, point, created_at
        )
        SELECT
            CAST(:title AS VARCHAR(200)),
            :content,
            CAST(:article_url AS VARCHAR(500)),
            :map_id,
            CAST(:category_cd AS VARCHAR(6)),
            CAST(:information_cd AS VARCHAR(6)),
            CAST(:shop_cd AS VARCHAR(6)),
            CAST(:author AS VARCHAR(100)),
            CAST(:keywords AS VARCHAR(100)),
            :point,
            NOW()
        WHERE NOT EXISTS (
            SELECT 1 FROM existing
        )
        RETURNING crawling_id
    )
```

- [ ] **Step 4: Add existing-row code-field update CTE**

Add this CTE after `inserted AS (...)` and before the final `SELECT`.

```python
    updated_existing AS (
        UPDATE crawling AS c
        SET
            information_cd = COALESCE(NULLIF(BTRIM(c.information_cd), ''), CAST(:information_cd AS VARCHAR(6))),
            shop_cd = COALESCE(NULLIF(BTRIM(c.shop_cd), ''), CAST(:shop_cd AS VARCHAR(6)))
        FROM existing AS e
        WHERE c.crawling_id = e.crawling_id
        RETURNING c.crawling_id
    )
```

- [ ] **Step 5: Update the final `SELECT`**

Replace the final query tail with this version.

```python
    SELECT crawling_id FROM inserted
    UNION ALL
    SELECT crawling_id FROM updated_existing
    UNION ALL
    SELECT crawling_id FROM existing
    WHERE NOT EXISTS (SELECT 1 FROM updated_existing)
    LIMIT 1
"""
```

- [ ] **Step 6: Run focused test and verify the import error is gone**

Run from `C:\dev\Project\SK-Connect`:

```powershell
$env:PYTHONPATH='C:\dev\Project\SK-Connect\etl\meal'
C:\Python314\python.exe -m pytest etl\meal\tests\test_stage4_backend_category_contract.py -v
```

Expected: FAIL only on Stage4 parameter wiring, not on missing constant or touch SQL text.

---

### Task 3: Wire Stage4Load Parameters

**Files:**
- Modify: `etl/meal/src/projects/save/stage4_load.py`

- [ ] **Step 1: Import `RESTAURANT_INFORMATION_CD`**

Update the constants import block.

```python
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
```

- [ ] **Step 2: Add `information_cd` to `_touch_last_checked_at` params**

Inside `_touch_last_checked_at`, add the new parameter.

```python
session.execute(text(QUERY_TOUCH_SHOP_CHECKED_AT), {
    "shop_id": record["existing_store_id"],
    "title": f"Checked - {store.get('name', 'unknown')}",
    "content": store.get("description", ""),
    "article_url": store.get("canonical_url", ""),
    "category_cd": None,
    "information_cd": RESTAURANT_INFORMATION_CD,
    "author": "System",
    "keywords": "",
    "point": float(store.get("rating", 0.0)),
})
```

- [ ] **Step 3: Rename `_load_crawling_and_reviews` parameter**

Change the method signature from `category_cd: str` to `shop_cd: str`.

```python
def _load_crawling_and_reviews(
    self,
    session: Session,
    store: Dict[str, Any],
    reviews: List[Dict[str, Any]],
    map_id: str,
    shop_cd: str,
):
```

- [ ] **Step 4: Pass code fields for the store crawling row**

In the first `QUERY_INSERT_CRAWLING` call inside `_load_crawling_and_reviews`, include these params.

```python
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
```

- [ ] **Step 5: Pass code fields for each review crawling row**

In the review loop, include the same code params.

```python
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
```

- [ ] **Step 6: Pass the actual input shop code from `execute()`**

In `execute()`, replace the `_load_crawling_and_reviews` call argument currently passing `RESTAURANT_CATEGORY_CD` with `shop_cd`.

```python
crawling_source_id = self._load_crawling_and_reviews(
    session,
    store,
    record.get("reviews", []) if change_plan["review"] else [],
    map_id,
    shop_cd,
)
```

- [ ] **Step 7: Run focused test and verify GREEN**

Run from `C:\dev\Project\SK-Connect`:

```powershell
$env:PYTHONPATH='C:\dev\Project\SK-Connect\etl\meal'
C:\Python314\python.exe -m pytest etl\meal\tests\test_stage4_backend_category_contract.py -v
```

Expected: PASS.

- [ ] **Step 8: Commit this unit if requested**

```powershell
git add etl\meal\src\core\constants.py etl\meal\src\projects\save\stage4_load.py etl\meal\tests\test_stage4_backend_category_contract.py
git commit -m "fix: persist meal crawling code fields"
```

---

### Task 4: Regression And DB Verification

**Files:**
- Verify: `etl/meal`
- Verify: local PostgreSQL container after fresh DB recreation

- [ ] **Step 1: Run full meal test suite**

Run from `C:\dev\Project\SK-Connect`:

```powershell
$env:PYTHONPATH='C:\dev\Project\SK-Connect\etl\meal'
C:\Python314\python.exe -m pytest etl\meal\tests -v
```

Expected: PASS.

- [ ] **Step 2: Recreate local DB when the user explicitly wants fresh local data**

This deletes the local Docker volume. Run only after explicit confirmation.

```powershell
docker compose -f database\docker-compose.yml down -v
docker compose -f database\docker-compose.yml up -d
```

Expected: `sk_connect_db` starts cleanly.

- [ ] **Step 3: Run the meal ETL path that writes crawling rows**

Use the project’s normal meal ETL command for the target `SCxx` batch. If there is no approved single command for the current dataset, do not invent one; ask for the exact runner command.

- [ ] **Step 4: Verify DB values**

Run after Stage 4 writes rows:

```powershell
docker exec sk_connect_db psql -U user -d service -c "SELECT category_cd, information_cd, shop_cd, count(*) AS count FROM crawling GROUP BY category_cd, information_cd, shop_cd ORDER BY category_cd, information_cd, shop_cd;"
```

Expected for meal rows:

```text
category_cd = CA01
information_cd = IC01
shop_cd LIKE SC%
```

- [ ] **Step 5: Verify no meal crawling code blanks remain for newly loaded rows**

Run:

```powershell
docker exec sk_connect_db psql -U user -d service -c "SELECT count(*) AS bad_meal_crawling_rows FROM crawling WHERE category_cd = 'CA01' AND (information_cd IS DISTINCT FROM 'IC01' OR shop_cd IS NULL OR btrim(shop_cd) = '');"
```

Expected:

```text
bad_meal_crawling_rows = 0
```

---

## Self-Review

- Spec coverage: `crawling` 적재 단계에서 `information_cd/shop_cd`를 저장한다는 요구는 Task 2와 Task 3이 구현한다.
- Scope control: DB 스키마, 기존 DB backfill, `analysis` 보정, IT 뉴스 파이프라인은 제외했다.
- Type consistency: `category_cd`는 항상 `CA01`, `information_cd`는 항상 `IC01`, `shop_cd`는 Stage 4 입력 `SCxx`를 사용한다.
- Risk: `_load_crawling_and_reviews`는 private method지만 기존 테스트가 직접 호출하므로 테스트도 함께 새 `shop_cd` 인자로 갱신한다.
