# post_analysis 테스트 기준 (통합)

함수 계약·시나리오·가드레일·**실행 방법**의 단일 기준 문서.  
Skill `code-integrity-and-testing` · [function-inventory.md](function-inventory.md) · [integrity-and-testing-standards.md](integrity-and-testing-standards.md)와 함께 사용한다.

> **전제:** 별도 “테스트 전용 DB”를 두지 않고 **평소 쓰는 PostgreSQL**(로컬 복원본 등)을 쓸 수 있다.  
> **자동 테스트·스모크는 `analysis`에 MERGE(INSERT/UPDATE)를 하지 않는다.** 쓰기 검증은 **간접**(mock·호출 인자·DataFrame assert).

---

## 1. 목적

| 목표 | 설명 |
|------|------|
| 기능 변경 회귀 | 코드 수정 후 필터·MERGE 규칙·파이프라인 순서 유지 |
| 데이터 규칙 회귀 | Enum·COALESCE·IC02/CA07 등 불변 규칙 |
| DB 보호 | pytest 실행 중 **기존 `analysis` 행 훼손 방지** |

**쓰기 유일 경로:** `postgresql.run_query.merge_analysis_data` (`autocommit`, rollback 없음).

---

## 2. 현재 구현 상태 (2026-05-20)

| 항목 | 상태 |
|------|------|
| pytest 테스트 | **65건 구현·통과** (`tests/unit/`) |
| G1 merge 차단 | `tests/conftest.py` autouse |
| 설정 | `pytest.ini` |
| 의존성 | `requirements.txt` — `pytest>=8.0.0` |
| 테스트 docstring | 각 `test_*` 함수에 시나리오 ID·목적 기재 |
| P1 `readonly_smoke` | **미구현** (마커·설정만 준비) |
| CI | **미연동** |

### 2.1 파일 ↔ 시나리오 매핑

| 테스트 파일 | 건수 | 시나리오 범위 |
|-------------|------|----------------|
| `test_g1_merge_blocked.py` | 1 | G1 가드 |
| `test_l0_errors.py` | 7 | PA-L0-ERR-001~006 |
| `test_l0_constants.py` | 4 | PA-L0-CST-001~004 |
| `test_l0_singleton.py` | 2 | PA-L0-SNG-001~002 |
| `test_l0_shop_filter.py` | 7 | PA-L0-SHP-001~007 |
| `test_l0_bert_predict.py` | 5 | PA-L0-BERT-001~005 |
| `test_l0_bert_keywords.py` | 12 | PA-L0-BKW-001~012 |
| `test_l0_pipeline_args.py` | 3 | PA-L0-PLN-001~003 |
| `test_l0_keywords_model.py` | 2 | PA-L0-LLM-001~002 |
| `test_l2_merge_mock.py` | 3 | PA-L2-PG-MRG-001, 002, 010~012(간접) |
| `test_l2_get_reviews_indirect.py` | 3 | PA-L2-GRV-001, 004, 005 |
| `test_l2_analyze_sentimental_indirect.py` | 3 | PA-L2-SNT-002~004 |
| `test_l3_analyze_keywords_indirect.py` | 2 | PA-L3-LLM-002, 006 |
| `test_l3_analyze_keywords_bert_indirect.py` | 7 | PA-L3-KW-001~007 |
| `test_l3_run_pipeline_indirect.py` | 3 | PA-L2-PLN-001~003 |

### 2.2 아직 코드화되지 않은 시나리오 (추가 시 docstring·ID 동일 규칙)

| ID | 비고 |
|----|------|
| PA-L2-GRV-002, 003, 006~008 | get_reviews 추가 분기 (004: CA07→IC02·shop 스킵 반영) |
| PA-L2-SNT-001, 005~006 | analyze_sentimental |
| PA-L3-KW-008~009 | analyze_keywords 행별 실패·no_pending 변형 |
| PA-L3-LLM-001, 003~005, 007~009 | analyze_keywords_by_llm |
| PA-L2-PLN-004, PA-L3-PLN-001~002 | pipeline 실패·E2E |
| PA-L2-PG-MRG-003~005 | merge 전처리 세부 |
| PA-L1-* | READ mock / readonly_smoke |

### 2.3 `pytest` 통과가 증명하는 것 / 하지 않는 것

| 증명함 | 증명하지 않음 |
|--------|----------------|
| G1: 테스트 중 실 MERGE 차단 | 실제 DB 연결·SELECT 스모크 |
| P0 순수 로직·상수·shop·BERT(mock) | OpenAI / HF Hub 실 호출 |
| P2/P3: merge·배치 **간접** 규칙 | `run_pipeline()` end-to-end 실 DB |
| MERGE SQL `COALESCE` 불변 | 운영 DB 행 품질·건수 invariant |

---

## 3. 테스트 실행 방법

### 3.1 사전 준비

```powershell
cd c:\dev\project\SK-Connect\ai\post_analysis
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

- 작업 디렉터리는 **`post_analysis` 루트** (`pytest.ini`, `pythonpath=.` 기준).
- **DB 연결 불필요** — 기본 44건은 mock·메모리만 사용.

### 3.2 기본 실행 (일상)

```powershell
python -m pytest
```

`pytest.ini`의 `addopts` 때문에 `readonly_smoke`, `slow` 마커 테스트는 제외된다.

**기대 결과 예:**

```text
44 passed in X.XXs
```

### 3.3 상세·리포트

| 목적 | 명령 |
|------|------|
| 테스트 이름 + docstring 확인 | `python -m pytest -v` |
| 실패 위치 요약 | `python -m pytest -v --tb=short` |
| 수집만 (실행 없음) | `python -m pytest --collect-only -q` |
| HTML 리포트 | `pip install pytest-html` 후 `python -m pytest --html=reports/pytest-report.html --self-contained-html` |
| JUnit XML (CI용) | `python -m pytest --junitxml=reports/junit.xml` |
| 특정 파일만 | `python -m pytest tests/unit/test_l0_shop_filter.py -v` |
| 키워드 필터 | `python -m pytest -k "shop" -v` |
| 시나리오 ID 필터 | `python -m pytest -k "PA-L0-SHP" -v` |

### 3.4 pytest 마커

| 마커 | 포함 방법 | DB·MERGE |
|------|-----------|----------|
| (기본) | `pytest` | MERGE **차단**, DB 대부분 미사용 |
| `merge_mock` | `pytest -m merge_mock` | PostgreDB **mock** + merge 함수 실행(cursor mock) — **실 DB 쓰기 없음** |
| `readonly_smoke` | `pytest -m readonly_smoke` | READ만(구현 시); MERGE는 **차단** |
| `slow` | `pytest -m slow` | BERT 실모델 등(미구현) |
| 전체 | `pytest -m ""` | 마커 필터 해제 (`addopts` 무시하려면 `-o addopts=`) |

```powershell
# merge_mock 3건 추가 실행 (총 44 + merge_mock 중복 없으면 44 유지, merge_mock만 따로)
python -m pytest tests/unit/test_l2_merge_mock.py -v
```

### 3.5 환경 변수

| 변수 | 기본 | 설명 |
|------|------|------|
| `POST_ANALYSIS_TEST_BLOCK_MERGE` | `1` | `1`: merge 실호출 차단 / `0`: 차단 해제 (**로컬 수동만**, CI·일상 사용 금지) |

```powershell
# 차단 해제는 권장하지 않음 — analysis 테이블 변경 위험
$env:POST_ANALYSIS_TEST_BLOCK_MERGE="0"
python -m pytest
```

### 3.6 코드 수정 후 권장 절차

1. `post_analysis` 루트에서 `python -m pytest -v`
2. **44 passed** 확인
3. 실패 시 `-k`로 해당 시나리오 ID만 재실행해 원인 좁히기
4. 배치·DB 동작은 **테스트가 아닌** `python pipeline.py` / 단계 스크립트로 별도 검증

### 3.7 파이프라인 실행과 테스트 구분

| 작업 | 명령 | analysis 변경 |
|------|------|----------------|
| **자동 테스트** | `python -m pytest` | **없음** (G1) |
| **실제 배치** | `python pipeline.py` / `get_reviews.py` 등 | **있음** (MERGE) |
| DB 연결 확인 | `python -m postgresql` | READ 위주 |

테스트 통과 ≠ 배치 성공. 배치는 `.env`의 `PG*` DB에 직접 영향을 준다.

---

## 4. 가드레일 (G1~G6)

### G1. DB 쓰기 금지

| 규칙 | 구현 위치 |
|------|-----------|
| G1-1 | `tests/conftest.py` — `merge_analysis_data` autouse 차단 |
| G1-2 | 배치 테스트 — `get_*` + `merge` patch |
| G1-3 | PA-L2-PG-MRG-010~012 실 DB **미구현** |

### G2. pytest 기본 범위

`pytest.ini`:

```ini
addopts = -m "not readonly_smoke and not slow"
```

### G3~G6

| ID | 요약 |
|----|------|
| G3 | Level 2·3 — merge patch + DataFrame assert |
| G4 | 테스트 `crawling_id` 음수·대역번호 |
| G5 | `reset_singletons` fixture (필요 시) |
| G6 | LLM·chain mock |

---

## 5. 구현 로드맵

| Phase | 등급 | 상태 | 산출물 |
|-------|------|------|--------|
| P0 | 0 | **완료** | `test_l0_*`, `test_g1_*` |
| P1 | 1 | 대기 | `readonly_smoke`, `test_l1_*` |
| P2 | 2 간접 | **핵심 완료** | `test_l2_*` |
| P3 | 3 간접 | **핵심 완료** | `test_l3_*` |

---

## 6. 테스트 ID 규칙

`PA-L{등급}-{모듈}-{순번}` — 분류: 정상 · 실패 · 경계 · 불변 · 회귀  
구현된 테스트 함수 docstring에 동일 ID를 명시한다.

---

## 7. 시나리오 요약

### Phase P0 — Level 0 (구현 완료)

| 영역 | ID | 테스트 파일 |
|------|-----|-------------|
| errors | ERR-001~006 | `test_l0_errors.py` |
| constant | CST-001~004 | `test_l0_constants.py` |
| singleton | SNG-001~002 | `test_l0_singleton.py` |
| shop | SHP-001~007 | `test_l0_shop_filter.py` |
| bert | BERT-001~005 | `test_l0_bert_predict.py` |
| pipeline CLI | PLN-001~003 | `test_l0_pipeline_args.py` |
| Keywords | LLM-001~002 | `test_l0_keywords_model.py` |

### Phase P2/P3 — 간접 (핵심 구현 완료)

| 영역 | 구현 ID | 미구현(추가 후보) |
|------|---------|------------------|
| merge | MRG-001, 002, 010~012 | MRG-003~005 |
| get_reviews | GRV-001, 004, 005 | GRV-002, 003, 006~008 |
| sentimental | SNT-002, 003 | SNT-001, 004~006 |
| llm | LLM-002, 006 | LLM-001, 003~005, 007~009 |
| pipeline | PLN-001~003 | PLN-004, PLN-001~002(E2E) |

---

## 8. 디렉터리 레이아웃

```
post_analysis/
├── pytest.ini
├── requirements.txt          # pytest>=8.0.0
├── docs/testing.md           # 본 문서
└── tests/
    ├── conftest.py           # G1 merge 차단, reset_singletons
    └── unit/
        ├── test_g1_merge_blocked.py
        ├── test_l0_*.py        # 7 files
        ├── test_l2_*.py        # 3 files
        └── test_l3_*.py        # 2 files
```

---

## 9. 체크리스트

- [x] 통합 기준 문서 (`testing.md`)
- [x] G1 `conftest.py` merge 차단
- [x] P0 unit (28건)
- [x] G1 테스트 (1건)
- [x] P2/P3 간접 핵심 (13건)
- [x] 테스트 함수 docstring
- [x] 로컬 `pytest` 44 passed 검증
- [ ] `readonly_smoke` 구현
- [ ] 미구현 시나리오 추가
- [ ] CI `pytest` job

---

## 10. 관련 문서

- [function-inventory.md](function-inventory.md)
- [integrity-and-testing-standards.md](integrity-and-testing-standards.md)
- 구 문서: [test-scenarios.md](test-scenarios.md), [test-guardrails.md](test-guardrails.md) → 본 문서로 통합

---

## 변경 이력

| 날짜 | 내용 |
|------|------|
| 2026-05-20 | `test-scenarios.md` + `test-guardrails.md` 통합 |
| 2026-05-20 | 테스트 44건 구현·실행 방법·현재 상태 섹션 반영 |
