# it_news 테스트 기준 (통합)

함수 계약·**테스트 케이스**·가드레일·실행 방법의 단일 기준 문서.  
Skill `code-integrity-and-testing` · [function-inventory.md](./function-inventory.md) · [integrity-and-testing-standards.md](./integrity-and-testing-standards.md)와 함께 사용한다.

> **전제:** 별도 테스트 DB 없이도 **Level 0**은 DB·네트워크 없이 실행 가능하다.  
> **자동 pytest는 `crawling` 테이블 MERGE를 하지 않는다.** 쓰기 검증은 mock·DataFrame assert(간접).

---

## 1. 현재 구현 상태

| 항목 | 상태 |
|------|------|
| 테스트 케이스 문서 | **본 문서** (2026-05-20) |
| `tests/` · `pytest.ini` | **구현** (`tests/unit/` 63 tests) |
| 시나리오 ID | `IT-L{등급}-{모듈}-{순번}` |
| G1 MERGE 차단 | `tests/conftest.py` autouse |
| 의존성 | `requirements.txt` — `pytest>=8.0.0` |

### 1.1 Phase 요약

| Phase | 등급 | 시나리오(문서) | pytest 구현 |
|-------|------|----------------|-------------|
| P0 | Level 0 | 38 | **34** (`test_l0_*`) |
| G1 | 가드 | 2 | **2** (`test_g1_*`) |
| P1 | Level 1 | 6 | **6** (`test_l1_*`) |
| P2 | Level 2 | 12 | **12** (`test_l2_*`) |
| P3 | Level 3 | 8 | **7** (`test_l3_*`; `IT-L3-CRAWL-004` slow 미구현) |
| **합계** | | **66** | **63** (문서 대비 3건은 통합·slow로 생략 또는 G1-002 문서 전용) |

### 1.2 파일 ↔ 시나리오 매핑

| 테스트 파일 | 대표 시나리오 |
|-------------|----------------|
| `test_g1_merge_blocked.py` | IT-L1-G1-001~002 |
| `test_l0_utils.py` | IT-L0-UTIL-001~008 |
| `test_l0_preprocess.py` | IT-L0-PRE-001~010 |
| `test_l0_errors_constants.py` | IT-L0-ERR-001~002, CST-001~004 |
| `test_l0_config.py` | IT-L0-CFG-001~003 |
| `test_l0_geek_slicing.py` | IT-L0-GEEK-001~003 |
| `test_l0_pt_slicing.py` | IT-L0-PT-001~002 |
| `test_l1_wm_mock.py` | IT-L1-WM-001~002 |
| `test_l1_preprocess_io.py` | IT-L1-PRE-001~002, UTIL-001 |
| `test_l1_mrg_read.py` | IT-L1-MRG-001 |
| `test_l2_mrg_mock.py` | IT-L2-MRG-001~003 (`merge_mock`) |
| `test_l2_save_indirect.py` | IT-L2-SAVE-001~003 |
| `test_l2_crawl_indirect.py` | IT-L2-CRAWL-001~003 |
| `test_l2_util_csv.py` | IT-L2-UTIL-001 |
| `test_l2_cln_indirect.py` | IT-L2-CLN-001 |
| `test_l2_pln_indirect.py` | IT-L2-PLN-001 |
| `test_l3_geek_mock.py` | IT-L3-GEEK-001~004 |
| `test_l3_pt_mock.py` | IT-L3-PT-001~004 |
| `test_l3_pln_indirect.py` | IT-L3-PLN-002 |

---

## 2. 테스트 ID 규칙

형식: **`IT-L{등급}-{모듈}-{순번}`**

| 분류 태그 | 의미 | 예 |
|-----------|------|-----|
| (접미 없음) | 정상 | IT-L0-UTIL-001 |
| 문서 내 «실패» | 실패·예외 | IT-L0-CFG-002 |
| «경계» | 0/최대/빈 값 | IT-L0-PRE-005 |
| «불변» | INV-* 규칙 | IT-L0-UTIL-003 |
| «회귀» | 버그 수정 시 추가 | IT-L0-xxx-9xx |

**모듈 코드**

| 코드 | 대상 |
|------|------|
| UTIL | `common.utils` |
| PRE | `common.preprocess` |
| ERR | `common.errors` |
| CST | `common.constant` |
| CFG | `postgresql.config` |
| WM | `postgresql.watermark` |
| MRG | `postgresql.run_query` |
| CRAWL | `common.crawling_http` |
| GEEK | `crawling_thread_geeknews` (slicing·thread) |
| PT | `crawling_thread_pytorch` (slicing·thread) |
| CLN | `cleaning.cleaning_threads` |
| SAVE | `save.save_threads` |
| PLN | `pipeline.run_pipeline` |
| G1 | `tests/conftest` 가드 |

구현 시 각 `test_*` docstring에 **동일 ID**를 명시한다.

### 2.1 테스트 수정 시 침범 검토 (Skill §9.1)

Skill `code-integrity-and-testing` — `reference-standards.md` **§9.1 테스트 수정·추가 판단 (침범 검토)** (Cursor skills 경로).

기능 구현 시 **기존 `IT-L*`·assert를 구현에 맞게 무조건 고치지 않는다.** 검토 없이 조정하면 이전 방어(«불변»·**INV-***)가 약해지거나 회귀 신호가 사라져 테스트가 **의미 없어질** 수 있고, 작업은 **코드 + 테스트 재작성 2배**에 가깝다.

| it_news 적용 | 행동 |
|--------------|------|
| «불변»·INV-01~08 (예: IT-L0-UTIL-003, IT-L2-CRAWL-002) | assert 유지; 깨지면 **구현** 또는 **testing.md에 계약 변경 기록** |
| 신규 크롤 동작 (목록 워터마크·조기 종료) | IT-L3-GEEK/PT **새 순번** 추가; 기존 001을 전면 교체하지 않음 |
| IT-L3-*-003 위임(patch) | 목록·워터마크 로직은 **001·004 등 별도 ID**가 검증 |
| G1 | **절대** 우회·약화 금지 |

**수정 전 체크 (요약):** (1) 계약 변경인가 mock 동기화인가 (2) INV assert 약화 없음 (3) 신규 동작은 새 ID (4) 구현 버그인데 테스트만 통과시키지 않았는가.

---

## 3. 가드레일 (설계)

### G1. DB 쓰기 금지

| 규칙 | 구현 예정 |
|------|-----------|
| G1-1 | `tests/conftest.py` — `insert_crawling_batch` autouse 차단 |
| G1-2 | `IT-L1-G1-001` — 차단 시 `RuntimeError` 또는 skip 메시지 |
| G1-3 | 환경변수 `IT_NEWS_TEST_BLOCK_MERGE` 기본 `1`; `0`은 로컬 수동만 |

**쓰기 경로:** `insert_crawling_batch`만. `save_csv`는 **tmp_path** fixture로 격리.

### G2. pytest 기본 (예정)

```ini
# pytest.ini (구현 시)
addopts = -m "not readonly_smoke and not slow"
pythonpath = .
```

### G3~G5

| ID | 요약 |
|----|------|
| G3 | Level 2 — `PostgreDB` mock + cursor `execute` assert |
| G4 | CSV·경로 테스트는 `tmp_path` / `monkeypatch` |
| G5 | `PostgreDB` 싱글톤 — 테스트 간 `reset` fixture(필요 시) |

---

## 4. 시나리오 카탈로그 (요약표)

### 4.1 P0 — Level 0 (38건)

| 모듈 | ID 범위 | 대상 함수 | 분류 |
|------|---------|-----------|------|
| UTIL | 001~010 | `build_csv_path`, …, `is_created_after_watermark`, `parse_discourse_iso_datetime`, `extract_korean_relative_time_from_text` | 정상·실패·불변 |
| PRE | 001~010 | `separate_success_and_fail`, `cleaning_*`, `wrap_article_url_as_html_anchor`, `cleaning_data_in_df` | 정상·실패·불변 |
| ERR | 001~003 | `EtlErrors.*` | 불변 |
| CST | 001~004 | `Service`, `Stage`, `Status`, `CodeTable` | 불변 |
| CFG | 001~002 | `require_env`, `build_dsn` | 실패·불변 |
| GEEK | 001~003 | `slicing_thread`, `slicing_created_at`(geeknews) | 정상·실패 |
| PT | 001~002 | `slicing_thread`, `slicing_created_at`(pytorch fixture) | 정상 |
| CRAWL | 001 | `user_agent_headers` | UTIL과 중복 시 UTIL만 구현 |

### 4.2 G1 — 가드 (2건)

| ID | 목적 |
|----|------|
| IT-L1-G1-001 | merge 차단 autouse 동작 |
| IT-L1-G1-002 | 차단 해제 env는 테스트에서 기본 사용 안 함(문서만) |

### 4.3 P1 — Level 1 (6건)

| ID | 대상 |
|----|------|
| IT-L1-WM-001 | `get_last_success_date()` — DB empty → default (mock) |
| IT-L1-WM-002 | `get_last_success_date(Service.GEEKNEWS)` — prefix SQL (mock) |
| IT-L1-MRG-001 | `fetch_crawling_dataframe` — mock cursor |
| IT-L1-PRE-001 | `get_crawling_success_for_cleaning` — tmp raw CSV 트리 |
| IT-L1-PRE-002 | `get_cleaning_success_for_save` — tmp cleaning CSV |
| IT-L1-UTIL-001 | `collect_crawling_success_datas` — min_run_folder_date 필터 |

### 4.4 P2 — Level 2 간접 (12건)

| ID | 대상 |
|----|------|
| IT-L2-MRG-001 | `insert_crawling_batch` empty → no execute |
| IT-L2-MRG-002 | `insert_crawling_batch` — MERGE SQL·Jsonb payload (mock) |
| IT-L2-MRG-003 | `_row_to_crawling_dict` / `map_id` 정규화 (단위) |
| IT-L2-SAVE-001 | `save_threads` — 0행 스킵 |
| IT-L2-SAVE-002 | `save_threads` — 기존 thread 필터 (mock fetch) |
| IT-L2-SAVE-003 | `save_threads` — insert 예외 시 전체 fail (mock) |
| IT-L2-CRAWL-001 | `run_crawl_and_save` — parse 실패 → fail row |
| IT-L2-CRAWL-002 | `run_crawl_and_save` — `created_at` 워터마크 필터 |
| IT-L2-CRAWL-003 | `run_crawl_and_save` — tmp_path CSV 생성 |
| IT-L2-UTIL-001 | `save_csv` — tmp_path 기록 |
| IT-L2-CLN-001 | `cleaning_threads` — mock load·전처리·CSV (patch) |
| IT-L2-PLN-001 | `run_pipeline` — 4단계 호출 순서 (patch) |

### 4.5 P3 — Level 3 간접 (8건)

| ID | 대상 |
|----|------|
| IT-L3-GEEK-001 | `get_article_list` — HTML 목록·워터마크 필터 |
| IT-L3-GEEK-004 | `get_article_list` — 전 페이지 워터마크 이하 시 조기 종료 |
| IT-L3-GEEK-002 | `parse_article` — mock response·dict 키 |
| IT-L3-PT-001 | `get_article_list` — JSON 목록·워터마크 필터 |
| IT-L3-PT-004 | `get_article_list` — 전 페이지 구간 워터마크 이하 시 조기 종료 |
| IT-L3-PT-002 | `parse_article` — HTML+JSON mock |
| IT-L3-GEEK-003 | `crawling_thread_geeknews` — `run_crawl_and_save` 위임 (patch) |
| IT-L3-PT-003 | `crawling_thread_pytorch` — 위임 (patch) |
| IT-L3-PLN-002 | `run_pipeline` — 한 단계 예외 전파 (patch) |
| IT-L3-CRAWL-004 | `run_crawl_and_save` — REQUEST_DELAY sleep mock (선택·slow) |

---

## 5. 시나리오 상세 (계약 기반)

아래는 구현·리뷰용 최소 계약 필드다. pytest docstring에 ID·목적을 옮긴다.

### 5.1 `common.utils`

#### IT-L0-UTIL-001 — `format_hhmmss` 정상

| 항목 | 내용 |
|------|------|
| 대상 | `format_hhmmss` |
| 유형 / 안전성 | A / 0 |
| 입력 | `datetime(2026, 4, 21, 12, 52, 1)` |
| 기대 | `"125201"` |
| 불변 | strftime `%H%M%S` |

#### IT-L0-UTIL-002 — `parse_segment_int`

| 항목 | 내용 |
|------|------|
| 입력 | `"year=2026"`, `"year=abc"`, `"month=04"` |
| 기대 | `2026`, `None`, `4` |

#### IT-L0-UTIL-003 — `build_csv_path` 불변 (INV-01)

| 항목 | 내용 |
|------|------|
| 입력 | `Stage.CRAWLING`, `IC02`, `geeknews`, `SUCCESS`, `2026-05-20 11:30:45` |
| 기대 | `process=raw/information_cd=IC02/year=2026/month=05/day=20/status=success/geeknews_113045.csv` |
| 실패 | 경로에 `process=cleaning` 아님 |

#### IT-L0-UTIL-004 — `information_cd_for_path`

| 항목 | 내용 |
|------|------|
| 입력 | 빈 DF, 열 없음, 단일 `IC02`, 혼합 mode |
| 기대 | `IC02`, `IC02`, `IC02`, mode 값 |

#### IT-L0-UTIL-005 — `korean_relative_time` (경계)

| 항목 | 내용 |
|------|------|
| 입력 | `"3시간전"`, `"방금"`, `"알수없음"`, `""` |
| 기대 | now−3h, now, `None`, `None` |
| 사전 | `now` 고정 fixture |

#### IT-L0-UTIL-006 — `coalesce_last_created_at`

| 항목 | 내용 |
|------|------|
| 입력 | `None`, `NaT`, 유효 datetime str |
| 기대 | `default_last_collected_at()`, 동일, 파싱된 datetime |

#### IT-L0-UTIL-007 — `default_last_collected_at` (INV-08)

| 항목 | 내용 |
|------|------|
| 기대 | `date.today() - 90일` 의 00:00:00 |
| 검증 | 날짜 부분만 assert (시간 00:00) |

#### IT-L0-UTIL-008 — `user_agent_headers`

| 항목 | 내용 |
|------|------|
| 기대 | `User-Agent` 키 존재, 값 = `CrawlingConstant.USER_AGENT` |

---

### 5.2 `common.preprocess`

#### IT-L0-PRE-001 — `separate_success_and_fail`

| 항목 | 내용 |
|------|------|
| 입력 | 2행: success/fail `state` |
| 기대 | success 1행·`state` 없음; fail 1행·`state` 없음 |

#### IT-L0-PRE-002 — `cleaning_special_characters`

| 항목 | 내용 |
|------|------|
| 입력 | title에 `\u200b`, content NBSP |
| 기대 | 제거·공백 정규 |

#### IT-L0-PRE-003 — `cleaning_continuous_newlines`

| 항목 | 내용 |
|------|------|
| 입력 | `"a\n\n\nb"` |
| 기대 | `"a\nb"` |

#### IT-L0-PRE-004 — `cleaning_continuous_spaces`

| 항목 | 내용 |
|------|------|
| 입력 | `"a  \t  b"` |
| 기대 | `"a b"` |

#### IT-L0-PRE-005 — `wrap_article_url_as_html_anchor` (경계·INV)

| 항목 | 내용 |
|------|------|
| 입력 | title+url 정상; url만; 매우 긴 title |
| 기대 | `<a href="…">…</a>`; 빈/짧은 처리; 총 길이 ≤500 근사 |
| 불변 | href는 escape된 원본 URL |

#### IT-L0-PRE-006 — `cleaning_data_in_df` 필수 결측 (실패)

| 항목 | 내용 |
|------|------|
| 입력 | `title` NaN 1행 |
| 기대 | 해당 행 `state=fail` (INV-05) |

#### IT-L0-PRE-007 — `cleaning_data_in_df` thread 중복

| 항목 | 내용 |
|------|------|
| 입력 | 동일 `thread` 2행 |
| 기대 | last 1행만 success |

#### IT-L0-PRE-008 — `cleaning_data_in_df` 정상 1행

| 항목 | 내용 |
|------|------|
| 입력 | 필수 컬럼 채움 |
| 기대 | `state=success`; text 정규화 적용 |

#### IT-L0-PRE-009 — `cleaning_data_in_df` created_at 혼합 포맷

| 항목 | 내용 |
|------|------|
| 입력 | geeknews/pyTorch 혼합 datetime 문자열 |
| 기대 | `format=mixed` 파싱 성공 행은 success |

#### IT-L0-PRE-010 — `separate_success_and_fail` 빈 DF

| 항목 | 내용 |
|------|------|
| 기대 | 두 빈 DataFrame |

---

### 5.3 `common.errors` · `common.constant`

#### IT-L0-ERR-001 — 메시지 비어 있지 않음

| 항목 | 내용 |
|------|------|
| 대상 | `EtlErrors.Crawl.created_at_not_found`, `Save.merge_insert_failed`, `Db.missing_env_var("X")` |
| 기대 | non-empty str |

#### IT-L0-ERR-002 — `unsupported_service` 포맷

| 항목 | 내용 |
|------|------|
| 입력 | 임의 service 객체 |
| 기대 | 메시지에 받은 값 repr 포함 |

#### IT-L0-CST-001 — `Service` URL·service

| 항목 | 내용 |
|------|------|
| 기대 | GEEKNEWS.url에 `hada.io`; `.service == "geeknews"` |

#### IT-L0-CST-002 — `Stage` 값 (INV-02)

| 항목 | 내용 |
|------|------|
| 기대 | CRAWLING=`raw`, CLEANING=`cleaning`, SAVE=`save` |

#### IT-L0-CST-003 — `CodeTable` IT·ETC

| 항목 | 내용 |
|------|------|
| 기대 | INFORMATION_IT=`IC02`, CATEGORY_ETC=`CA07` (INV-07) |

#### IT-L0-CST-004 — `ETL_CRAWL_LOOKBACK_DAYS`

| 항목 | 내용 |
|------|------|
| 기대 | `90` |

---

### 5.4 `postgresql.config`

#### IT-L0-CFG-001 — `require_env` 정상

| 항목 | 내용 |
|------|------|
| 사전 | `monkeypatch.setenv("PGUSER", "user")` |
| 기대 | `"user"` |

#### IT-L0-CFG-002 — `require_env` 실패

| 항목 | 내용 |
|------|------|
| 사전 | unset 또는 `""` |
| 기대 | `ValueError`, 메시지에 키명 |

#### IT-L0-CFG-003 — `build_dsn` 형식

| 항목 | 내용 |
|------|------|
| 사전 | PG* 5개 env |
| 기대 | `postgresql://user:password@host:port/db` |

---

### 5.5 `crawling` slicing (HTML fixture, Level 0)

#### IT-L0-GEEK-001 — `slicing_thread`

| 항목 | 내용 |
|------|------|
| 입력 | `https://news.hada.io/topic?id=123` |
| 기대 | `geeknews_123` (INV-03) |

#### IT-L0-GEEK-002 — `slicing_created_at` 실패

| 항목 | 내용 |
|------|------|
| 입력 | topicinfo에 상대시각 없는 soup |
| 기대 | `ValueError`, `EtlErrors.Crawl.created_at_not_found()` 메시지 |

#### IT-L0-GEEK-003 — `slicing_comment_count` 기본값

| 항목 | 내용 |
|------|------|
| 입력 | 요소 없는 soup |
| 기대 | `0` |

#### IT-L0-PT-001 — `slicing_thread`

| 항목 | 내용 |
|------|------|
| 입력 | `/t/slug/999` 형태 URL |
| 기대 | `pytorch_999` |

#### IT-L0-PT-002 — `slicing_created_at` ISO

| 항목 | 내용 |
|------|------|
| 입력 | `time.post-time[datetime]` fixture |
| 기대 | UTC naive datetime |

---

### 5.6 Level 1~3 (요약 계약)

#### IT-L1-WM-001 — `get_last_success_date` empty

| 항목 | 내용 |
|------|------|
| mock | `run_query` → `[(None,)]` |
| 기대 | `default_last_collected_at()`와 동일 날짜 부분 |

#### IT-L1-WM-002 — service별 MAX

| 항목 | 내용 |
|------|------|
| mock | `run_query_lst` → known datetime |
| 기대 | 동일 datetime 반환 |

#### IT-L1-PRE-001 — raw CSV 로드

| 항목 | 내용 |
|------|------|
| fixture | tmp `process=raw/.../geeknews_120000.csv` |
| mock | `get_last_success_date` |
| 기대 | 1행+, `_page_service=geeknews` |

#### IT-L2-MRG-002 — MERGE 호출

| 항목 | 내용 |
|------|------|
| mock | `PostgreDB.conn.cursor` |
| 입력 | 1행 minimal df |
| 기대 | `INSERT_CRAWLING` SQL 실행, Jsonb 인자 |

#### IT-L2-SAVE-002 — thread 필터

| 항목 | 내용 |
|------|------|
| mock | `fetch` thread `A`; df에 `A`,`B` |
| 기대 | insert는 `B`만 |

#### IT-L2-CRAWL-001 — parse 예외

| 항목 | 내용 |
|------|------|
| mock | `parse_article` raise |
| 기대 | fail df 1행, `error` 컬럼 |

#### IT-L2-CRAWL-002 — 워터마크

| 항목 | 내용 |
|------|------|
| 입력 | success row `created_at` ≤ threshold |
| 기대 | success df에서 제외 |

#### IT-L2-PLN-001 — 파이프라인 순서

| 항목 | 내용 |
|------|------|
| mock | 4개 진입 함수 |
| 기대 | 호출 순서 geeknews → pytorch → cleaning → save |

#### IT-L3-GEEK-002 — `parse_article` mock

| 항목 | 내용 |
|------|------|
| mock | `requests.get` HTML fixture |
| 기대 | dict에 `CrawlingColumn` 필수 키 존재 |

---

## 6. 구현 로드맵

| 순서 | 작업 | 산출물 |
|------|------|--------|
| 1 | P0 + G1 | `tests/unit/test_l0_*`, `test_g1_*`, `conftest.py` |
| 2 | P2 핵심 | `test_l2_mrg_mock.py`, `test_l2_save_indirect.py`, `test_l2_crawl_indirect.py` |
| 3 | P1 | `test_l1_wm_mock.py`, `test_l1_preprocess_io.py` |
| 4 | P3 | `test_l3_geek_mock.py`, `test_l3_pt_mock.py` |
| 5 | `requirements.txt` | `pytest>=8.0.0` |
| 6 | CI | (선택) |

### 6.1 예정 디렉터리

```
etl/it_news/
├── pytest.ini
├── requirements.txt          # + pytest
├── docs/testing.md           # 본 문서
└── tests/
    ├── conftest.py           # G1, tmp_path, env
    └── unit/
        ├── test_g1_merge_blocked.py
        ├── test_l0_utils.py
        ├── test_l0_preprocess.py
        ├── test_l0_errors_constants.py
        ├── test_l0_config.py
        ├── test_l0_geek_slicing.py
        ├── test_l0_pt_slicing.py
        ├── test_l1_*.py
        ├── test_l2_*.py
        └── test_l3_*.py
```

---

## 7. 실행 방법

```powershell
cd c:\dev\project\SK-Connect\etl\it_news
pip install -r requirements.txt
python -m pytest -v
```

**기대 결과:** `63 passed` (DB·실 HTTP 불필요)

| 작업 | 명령 | `crawling` 변경 |
|------|------|-----------------|
| 자동 테스트 | `python -m pytest` | **없음** (G1) |
| 실제 배치 | `python pipeline.py` | **있음** |

| 변수 | 기본 | 설명 |
|------|------|------|
| `IT_NEWS_TEST_BLOCK_MERGE` | `1` | `0`은 MERGE 차단 해제(로컬 수동만) |

---

## 8. 체크리스트

- [x] 테스트 케이스 문서 (`testing.md`)
- [x] 불변 규칙 (`integrity-and-testing-standards.md` INV-*)
- [x] `tests/` · G1 · pytest 63건 구현
- [ ] 로컬 `pytest` passed 확인(사용자 실행)
- [ ] `readonly_smoke` · CI

---

## 9. 관련 문서

- [function-inventory.md](./function-inventory.md)
- [integrity-and-testing-standards.md](./integrity-and-testing-standards.md)
- [design.md](./design.md)

---

## 변경 이력

| 날짜 | 내용 |
|------|------|
| 2026-05-20 | 함수 계약 기반 시나리오 66건 정의 (구현 전) |
| 2026-05-20 | §2.1 테스트 수정 침범 검토 (Skill §9.1 연계) |
