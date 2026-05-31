# Meal Code Resolution Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Meal ETL must persist `category_cd`, `information_cd`, and `shop_cd` without hardcoded code values in business logic.

**Architecture:** `shop_cd` is resolved from the existing execution input, which currently carries `SCxx` values through the legacy `category_cd` argument. Meal `category_cd` and `information_cd` are resolved through `CodeTableRepository` using configurable lookup keys, then passed explicitly into Stage3/Stage4 writes. Files that cannot access the DB, such as `HivePathBuilder`, use configuration instead of Python constants.

**Tech Stack:** Python, SQLAlchemy text query, Pydantic settings, PostgreSQL `codeT`, pytest.

---

## Scope

Included:
- Extend `CodeTableRepository` to preload all `codeT` rows and resolve category, information, shop, and table codes by group.
- Remove `RESTAURANT_CATEGORY_CD` and `RESTAURANT_INFORMATION_CD` from runtime business logic.
- Add configurable lookup keys to `Settings`.
- Resolve Stage3 normalized `category_cd` from `codeT`.
- Resolve Stage4 `category_cd`, `information_cd`, and `shop_cd` before DB load and pass them explicitly into SQL parameters.
- Use config for `HivePathBuilder` category partition conversion.
- Update focused tests and full meal test suite.

Excluded:
- DB schema changes.
- Existing local DB volume recreation.
- Backfill of existing `crawling` or `analysis` rows.
- IT news pipeline changes.

---

### Task 1: Code Table Resolver

**Files:**
- Modify: `etl/meal/src/core/constants.py`
- Modify: `etl/meal/src/core/repository/code_table_repository.py`
- Test: `etl/meal/tests/test_code_table_repository.py`

- [ ] Add one all-code query based on `QUERY_SELECT_ALL_CODES`.
- [ ] Build parent-group caches from `codeT.cd_upper` so child codes are grouped under parent names such as `category_cd`, `information_cd`, `shop_cd`, and `table_cd`.
- [ ] Add `get_category_code(key)`, `get_information_code(key)`, and keep existing shop/table methods on top of the same group resolver.
- [ ] Verify with `pytest etl/meal/tests/test_code_table_repository.py -v`.

### Task 2: Configurable Meal Code Keys

**Files:**
- Modify: `etl/meal/src/core/config.py`
- Modify: `etl/meal/src/core/storage/path_builder.py`
- Test: `etl/meal/tests/test_path_builder_contract.py`

- [ ] Add `MEAL_CATEGORY_CODE_KEY`, `MEAL_INFORMATION_CODE_KEY`, `MEAL_CATEGORY_CD`, and `SHOP_CODE_PREFIX` settings.
- [ ] Change `HivePathBuilder` to use `settings.MEAL_CATEGORY_CD` and `settings.SHOP_CODE_PREFIX`.
- [ ] Verify path tests with monkeypatched config values.

### Task 3: Stage3 Code Resolution

**Files:**
- Modify: `etl/meal/src/projects/process/stage3_validation_normalization.py`
- Test: `etl/meal/tests/test_stage3_menu_normalization.py`

- [ ] Resolve meal `category_cd` through `CodeTableRepository.get_category_code(settings.MEAL_CATEGORY_CODE_KEY)`.
- [ ] Keep execution input `SCxx` as `shop_cd`.
- [ ] Fail explicitly if the configured category key cannot be resolved.

### Task 4: Stage4 Code Resolution

**Files:**
- Modify: `etl/meal/src/projects/save/stage4_load.py`
- Test: `etl/meal/tests/test_stage4_backend_category_contract.py`

- [ ] Add `_resolve_code_context()` that resolves `category_cd`, `information_cd`, and `shop_cd`.
- [ ] Pass resolved codes into map, crawling, review, and touch-only SQL parameters.
- [ ] Keep SQL column additions from the previous Stage4 fix.
- [ ] Verify focused Stage4 tests.

### Task 5: Regression

**Files:**
- Verify: `etl/meal`

- [ ] Run `pytest etl/meal/tests -v`.
- [ ] Run a rollback SQL smoke check against local PostgreSQL if the local DB is available.
- [ ] Run `git diff --check`.

---

## Self-Review

- Spec coverage: This supersedes the earlier constant-based plan by moving code-value selection to `codeT`, config, and execution input.
- Scope control: No schema, backfill, local DB recreation, or IT news changes are included.
- Type consistency: `category_cd` means `CAxx`, `information_cd` means `ICxx`, and `shop_cd` means `SCxx` after resolution.
