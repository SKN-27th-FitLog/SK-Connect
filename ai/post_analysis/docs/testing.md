# post_analysis 테스트 기준 (통합)

함수 계약·시나리오·가드레일의 **단일 기준 문서**.  
Skill `code-integrity-and-testing` · [function-inventory.md](function-inventory.md) · [integrity-and-testing-standards.md](integrity-and-testing-standards.md)와 함께 사용한다.

> **전제:** 별도 “테스트 전용 DB”를 두지 않고 **평소 쓰는 PostgreSQL**(로컬 복원본 등)을 쓸 수 있다.  
> **자동 테스트·스모크는 `analysis`에 MERGE(INSERT/UPDATE)를 하지 않는다.** 쓰기 검증은 **간접**(mock·호출 인자·DataFrame assert).

---

## 1. 목적

| 목표 | 설명 |
|------|------|
| 기능 변경 회귀 | 코드 수정 후 필터·MERGE 규칙·파이프라인 순서 유지 |
| 데이터 규칙 회귀 | Enum·COALESCE·IC02/CA07 등 불변 규칙 |
| DB 보호 | pytest/스모크 실행 중 **기존 `analysis` 행 훼손 방지** |

**쓰기 유일 경로:** `postgresql.run_query.merge_analysis_data` (`autocommit`, rollback 없음).

---

## 2. 가드레일 (G1~G6)

### G1. DB 쓰기 금지 (DB 이름 allowlist 아님)

| 규칙 | 내용 |
|------|------|
| G1-1 | **모든** pytest에서 `merge_analysis_data` 실구현 실행 **금지** (`tests/conftest.py` autouse) |
| G1-2 | 배치 진입점 `get_reviews` / `analyze_sentimental` / `analyze_keywords_by_llm` / `run_pipeline` 단위 테스트는 **get_* + merge 전부 patch** 또는 merge만 차단된 상태에서 **간접 assert** |
| G1-3 | **실 MERGE 통합 테스트(PA-L2-PG-MRG-010~012)는 구현하지 않음** — 간접 시나리오로 대체 |

### G2. pytest 기본 실행 범위

```ini
# pytest.ini
addopts = -m "not readonly_smoke and not slow"
```

| 마커 | 의미 |
|------|------|
| (기본) | DB 미접속 또는 mock만 |
| `readonly_smoke` | **SELECT만** 허용; MERGE仍 차단 |
| `slow` | BERT 실모델 등 |

### G3. 간접 검증 (Level 2·3)

| 직접 (금지) | 간접 (권장) |
|-------------|-------------|
| MERGE 후 SELECT | `merge` patch → `call_args[0][0]` DataFrame assert |
| `run_pipeline()` 실실행 | 3단계 함수 patch → 호출 순서·kwargs |
| MRG-010~012 실 DB | MRG-001~005 cursor mock + SQL에 `COALESCE` 포함 assert |

### G4. fixture id

테스트 DataFrame의 `crawling_id`는 **음수** 또는 `9_000_000_001+` 대역 (실수 merge 시에도 운영 id와 충돌 최소화).

### G5. Singleton

테스트 module 시작 시 `PostgreDB` / `BertTokenizer` Singleton 캐시 초기화(필요 시).

### G6. LLM

`ChatOpenAI` / `chain.invoke` — unit에서 **항상** mock.

---

## 3. 구현 로드맵

| Phase | 등급 | 산출물 | DB |
|-------|------|--------|-----|
| P0 | 0 | `tests/unit/test_l0_*.py` | 없음 |
| P1 | 1 | mock read / `readonly_smoke` | READ만 |
| P2 | 2 간접 | `test_l2_*_indirect.py`, `test_l2_merge_mock.py` | **쓰기 없음** |
| P3 | 3 간접 | `test_l3_*_indirect.py` | **쓰기 없음** |

---

## 4. 테스트 ID 규칙

`PA-L{등급}-{모듈}-{순번}` — 분류 태그: 정상 · 실패 · 경계 · 불변 · 회귀

---

## 5. 시나리오 — Phase P0 (Level 0)

DB·MERGE 없음. **구현 완료 대상.**

### errors · `PostAnalysisErrors`

| ID | 검증 |
|----|------|
| PA-L0-ERR-001 | `_missing_columns_message` 포맷 |
| PA-L0-ERR-002~006 | 대표 메시지 + parametrized 나머지 |

### constant

| ID | 검증 |
|----|------|
| PA-L0-CST-001~004 | CodeTable, allowed_* columns, empty placeholders |

### singleton · shop · bert · pipeline · Keywords

| ID | 검증 |
|----|------|
| PA-L0-SNG-001~002 | Singleton 인스턴스 |
| PA-L0-SHP-001~007 | `_filter_rows_by_shop_match` |
| PA-L0-BERT-001~005 | `predict_sentiment` (model mock) |
| PA-L0-PLN-001~003 | `_parse_args` |
| PA-L0-LLM-001~002 | Pydantic `Keywords` |

---

## 6. 시나리오 — Phase P2/P3 간접 (MERGE·배치)

**공통:** `merge_analysis_data`는 patch 후 **호출 여부·DataFrame 내용**만 검증.

### merge (`postgresql/run_query`)

| ID | 간접 방식 |
|----|-----------|
| PA-L2-PG-MRG-001~005 | mock `PostgreDB` + cursor, `execute`·records 검증 |
| PA-L2-PG-MRG-010~012 | **실 DB 금지** → 001~005 + `MergeAnalysisConfig.MERGE_SQL`에 `COALESCE` |

### `get_reviews`

| ID | 간접 |
|----|------|
| GRV-001~002 | ValueError, merge 미호출 |
| GRV-003,007 | merge 미호출 |
| GRV-004,006,008 | merge 1회, df에 IC01·건수·created_dt |
| GRV-005 | 신규 0건, merge 미호출 |

### `analyze_sentimental` / `analyze_keywords_by_llm` / `run_pipeline`

| ID | 간접 |
|----|------|
| SNT-001~006 | get/merge patch, pending 건수·컬럼 |
| LLM-001~009 | chain mock + merge df |
| PLN-001~004 / PLN-001~002 | 단계 patch·순서·max_rows |

---

## 7. Phase P1 — READ 스모크 (선택)

| ID | 내용 | MERGE |
|----|------|-------|
| PA-L1-PG-010~014 | `_read_table` mock | 없음 |
| PA-RO-SMK-001 | `@pytest.mark.readonly_smoke` 연결+SELECT 1 | **G1 차단** |

---

## 8. pytest 레이아웃

```
tests/
├── conftest.py
├── unit/
│   test_l0_errors.py
│   test_l0_constants.py
│   test_l0_singleton.py
│   test_l0_shop_filter.py
│   test_l0_bert_predict.py
│   test_l0_pipeline_args.py
│   test_l0_keywords_model.py
│   test_l2_merge_mock.py
│   test_l2_get_reviews_indirect.py
│   test_l2_analyze_sentimental_indirect.py
│   test_l3_analyze_keywords_indirect.py
│   test_l3_run_pipeline_indirect.py
```

---

## 9. 환경

| 변수 | 용도 |
|------|------|
| `POST_ANALYSIS_TEST_BLOCK_MERGE` | `0`이면 merge 차단 해제(**로컬 수동만**, CI 금지) |

기본 pytest: **차단 on**.

---

## 10. 체크리스트

- [x] 통합 기준 문서 (`testing.md`)
- [x] G1 conftest merge 차단
- [x] P0 unit 테스트
- [x] P2/P3 간접 테스트 (핵심)
- [ ] `readonly_smoke` (선택)
- [ ] CI `pytest` job

---

## 변경 이력

| 날짜 | 내용 |
|------|------|
| 2026-05-20 | `test-scenarios.md` + `test-guardrails.md` 통합, 단일 DB·간접 검증 반영 |

## 구 문서

- [test-scenarios.md](test-scenarios.md) → 본 문서로 통합
- [test-guardrails.md](test-guardrails.md) → 본 문서로 통합
