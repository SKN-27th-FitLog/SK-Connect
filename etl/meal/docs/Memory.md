# SK-Connect ETL Meal — 프로젝트 이해 문서 (memory.md)

> **작성일:** 2026-04-24  
> **기반 스킬:** project-understanding  
> **상태:** 구현 분석 완료 / 변경 금지 (분석 전용 문서)

---

## 1. 현재 상태 (Current State)

### 프로젝트 목적

맛집(음식점) 데이터를 복수의 플랫폼(DiningCode, Naver, Google, Kakao)에서 크롤링하여 PostgreSQL DB에 정형화하여 적재하는 **ETL 파이프라인**.

- AWS Lambda 배포를 전제로 설계
- 로컬 `run_pipeline.py`로도 실행 가능
- 설계 기준서(`docs/Design.MD`)가 명시적으로 존재하며, 구현 우선순위의 준거

### 구현 완료 영역

| 영역 | 파일 | 상태 |
|------|------|------|
| 진입점 (로컬) | `run_pipeline.py` | ✅ 완료 |
| 진입점 (Lambda) | `src/handlers/lambda_handler.py` | ✅ 완료 |
| Stage별 단독 Handler | `src/handlers/stage1~5_handler.py` | ✅ 완료 |
| 파이프라인 오케스트레이터 | `src/pipeline/orchestrator.py` | ✅ 완료 |
| Registry (DI) | `src/core/registry.py` | ✅ 완료 |
| Stage 0 ~ 5 | `src/pipeline/stages/stage*.py` | ✅ 완료 |
| DiningCode Collector | `src/collectors/platforms/diningcode_collector.py` | ✅ 완료 (가장 구체적) |
| Naver/Google/Kakao Collector | `src/collectors/platforms/*.py` | ⚠️ 스텁 수준 |
| DiningCode Parser | `src/services/parsers/diningcode_parser.py` | ✅ 완료 (가장 상세) |
| Naver/Google/Kakao Parser | `src/services/parsers/*.py` | ⚠️ 스텁 수준 |
| 핵심 모델 | `src/core/models/models.py` | ✅ 완료 |
| 정책 Resolver | `src/core/policy/resolver.py` | ✅ 완료 |
| ReasonCode Enum | `src/core/policy/reason_code.py` | ✅ 완료 |
| Exception 계层 | `src/core/policy/exceptions.py` | ✅ 완료 |
| DB Repository | `src/core/repository/` | ✅ 완료 |
| Storage 유틸 | `src/core/storage/` | ✅ 완료 |
| SQL 상수 | `src/core/constants.py` | ✅ 완료 |
| 설정 관리 | `src/core/config.py` | ✅ 완료 |
| 테스트 | - | ❌ 미작성 |
| Metrics 파이프라인 | - | ❌ 미작성 |
| retry/reprocess 실행 흐름 | - | ❌ 미작성 |

---

## 2. 운영 컨텍스트 (Operating Context)

| 항목 | 내용 |
|------|------|
| **언어** | Python 3.x (asyncio 기반) |
| **프레임워크** | 없음 (순수 Python) |
| **DB** | PostgreSQL (SQLAlchemy + psycopg2-binary) |
| **크롤링** | Playwright (Chromium headless) |
| **HTML 파싱** | BeautifulSoup4 |
| **설정 관리** | pydantic-settings + `.env` 파일 |
| **데이터 모델** | Pydantic v2 (`BaseModel`) |
| **스토리지** | 로컬 파일시스템 → S3 (예정) |
| **실행 환경** | 로컬 (`run_pipeline.py`) / AWS Lambda (`lambda_handler.py`) |
| **비동기** | `asyncio`, `asyncio.Semaphore(3)` shard 제어 |

### 외부 의존성

- **PostgreSQL DB**: 코드테이블(`codeT`), `maps`, `shop`, `menu`, `crawling`, `images` 테이블 필요
- **Playwright**: Chromium 브라우저 설치 필요 (`playwright install chromium`)
- **DiningCode**: `https://www.diningcode.com` — 봇 탐지 있음 (수동 stealth 적용)

---

## 3. 구조 (Structure)

### 폴더 레이아웃

```
meal/
├── run_pipeline.py           # 로컬 진입점
├── target.csv                # 수집 seed (address_cd, category_cd)
├── .env                      # DB / 설정값 (gitignore)
├── requirements.txt
├── docs/
│   └── Design.MD             # 설계 기준서 (25개 챕터)
└── src/
    ├── core/
    │   ├── config.py          # pydantic-settings 기반 환경변수
    │   ├── constants.py       # SQL 쿼리 상수
    │   ├── registry.py        # Collector/Parser/Stage DI 팩토리
    │   ├── models/models.py   # Pydantic 데이터 모델
    │   ├── policy/
    │   │   ├── reason_code.py # ReasonCode Enum
    │   │   ├── exceptions.py  # 실패 의미 Exception 계층
    │   │   └── resolver.py    # Action 정책 결정 (source of truth)
    │   ├── repository/
    │   │   ├── database.py    # SQLAlchemy DB 연결
    │   │   └── code_table_repository.py  # codeT in-memory 캐시
    │   └── storage/
    │       ├── jsonl_writer.py   # JSONL read/write
    │       └── path_builder.py   # Hive 스타일 경로 생성
    ├── collectors/
    │   ├── base_collector.py  # Abstract: collect(), get_platform_name()
    │   └── platforms/
    │       ├── diningcode_collector.py  # ✅ 완전 구현
    │       ├── naver_collector.py       # ⚠️ 스텁
    │       ├── google_collector.py      # ⚠️ 스텁
    │       └── kakao_collector.py       # ⚠️ 스텁
    ├── services/parsers/
    │   ├── base_parser.py     # Abstract: parse_shop/menus/reviews/images
    │   ├── diningcode_parser.py  # ✅ 완전 구현 (437줄)
    │   ├── naver_parser.py       # ⚠️ 스텁
    │   ├── google_parser.py      # ⚠️ 스텁
    │   └── kakao_parser.py       # ⚠️ 스텁
    ├── pipeline/
    │   ├── orchestrator.py        # Stage 0~5 순차 실행
    │   └── stages/
    │       ├── base_stage.py
    │       ├── stage0_target_selection.py
    │       ├── stage1_raw_collection.py
    │       ├── stage2_candidate_parsing.py
    │       ├── stage3_validation_normalization.py
    │       ├── stage4_load.py
    │       └── stage5_fail_classification.py
    └── handlers/
        ├── lambda_handler.py   # AWS Lambda 진입점 (전체 파이프라인)
        ├── stage1_handler.py   # Stage 1 단독 Lambda handler
        ├── stage2_handler.py   # Stage 2 단독 Lambda handler
        ├── stage3_handler.py
        ├── stage4_handler.py
        └── stage5_handler.py
```

### 핵심 연결 구조

```
run_pipeline.py
    └─► PipelineOrchestrator(platform="DiningCode")
            └─► registry.py (get_collector / get_parser / get_stage)
                    ├─► DiningCodeCollector
                    ├─► DiningCodeParser
                    └─► Stage0 → Stage1 → Stage2 → Stage3 → Stage4 → Stage5
```

---

## 4. 데이터 흐름 (Data Flow)

```
target.csv
    ↓ [Stage 0: TargetSelection]
    DB codeT 조회 → address_name, category_name 매핑
    → List[{ address_cd, category_cd, search_query, source_platform }]

    ↓ [Stage 1: RawCollection]
    DiningCodeCollector.discover_stores(search_query)
    → 매장 프로필 URL 목록 (list.php 크롤링)
    DiningCodeCollector.collect(url)
    → HTML 스냅샷 + photo_data
    → 로컬 파일 저장 (Hive 경로)
    → JSONL metadata (shard_*.jsonl)
    → List[{ entity_id, raw_file_path, photo_data, status, ... }]

    ↓ [Stage 2: CandidateParsing]
    raw_file_path → open HTML
    DiningCodeParser.parse_shop/menus/reviews/images(html)
    → candidate JSONL 저장
    → List[{ entity_id, shop:{}, menus:[], reviews:[], images:[] }]

    ↓ [Stage 3: Validation & Normalization]
    _normalize_address() → address_cd / address_detail 분리
    _generate_dedup_key() → canonical_url > name_address > platform_id
    StoreModel 생성 (Pydantic 검증)
    → normalized JSONL 저장
    → List[{ store:{StoreModel}, menus:[], reviews:[], images:[] }]

    ↓ [Stage 4: Load]
    DB 트랜잭션 (Savepoint 격리):
    maps → shop → menu → images → crawling(증거+리뷰)
    → List[{ entity_id, status: success|fail }]

    ↓ [Stage 5: FailClassification]
    S1 실패 + S4 실패 수집
    PolicyResolver.resolve(reason_code, stage)
    → retry_allowed 판정
    → fail_ledger JSONL 저장
```

---

## 5. 핵심 모델/상태 (Core Models & State)

### StoreModel (Pydantic)
```python
entity_id, entity_ref, name, shop_cd, address_cd, address_detail,
latitude, longitude, rating, canonical_url,
source_platform, source_internal_id,
dedup_key, dedup_key_type, dedup_rule_version
```

### FailLedgerModel (Pydantic)
```python
batch_id, stage, entity_type, entity_id, entity_ref,
reason_code, action, detail, retry_count, created_at
```

### Stage 간 payload 계약 (비공식 dict)

| Stage 출력 | 핵심 키 |
|-----------|--------|
| Stage 0 → 1 | `address_cd`, `category_cd`, `search_query`, `source_platform` |
| Stage 1 → 2 | `entity_id`, `raw_file_path`, `photo_data`, `status` |
| Stage 2 → 3 | `entity_id`, `entity_ref`, `shop{}`, `menus[]`, `reviews[]`, `images[]` |
| Stage 3 → 4 | `store{StoreModel}`, `menus[]`, `reviews[]`, `images[]` |
| Stage 5 입력 | 모든 실패 dict (S1 + S4) |

> **⚠️ 주의:** Stage 간 payload는 Pydantic 모델이 아닌 `Dict[str, Any]`로 전달됨 — 타입 안전성 없음

### ReasonCode (Enum)

| 분류 | 코드 |
|------|------|
| Network | NETWORK_ERROR, PROXY_ERROR, TIMEOUT |
| Platform | SELECTOR_MISMATCH, BOT_DETECTED, NOT_FOUND, INVALID_URL |
| Data | INVALID_DATA_FORMAT, MISSING_REQUIRED_FIELD, NOT_RESTAURANT_ENTITY |
| Dedup | CONFLICTING_DEDUP_SIGNALS |
| DB/System | DB_CONNECTION_ERROR, DB_CONSTRAINT_VIOLATION, UNDEFINED_CODE_DETECTED |
| 기타 | UNKNOWN_ERROR, INTERNAL_PIPELINE_ERROR |

### Action (Enum)
`RETRY` / `REPROCESS` / `DROP` / `WARN` / `CRITICAL`

---

## 6. 설계 결정 및 관례 (Decisions & Conventions)

| 결정 항목 | 내용 |
|----------|------|
| **책임 분리** | Stage=처리, Resolver=정책, Exception=의미, FailLedger=운영기록 |
| **DB 코드 하드코딩 금지** | address_cd, shop_cd, category_cd는 반드시 codeT 조회 |
| **SQL 상수화** | constants.py에서만 정의, inline 금지 |
| **JSONL 중심** | 모든 중간 산출물(raw metadata, candidate, normalized, fail_ledger)은 JSONL |
| **overwrite 금지** | raw, JSONL 모두 append 또는 신규 파일 |
| **Hive 경로** | `process=X/service=X/year=X/month=X/day=X/status=X/category_cd=X/stage=X/batch_id=X` |
| **파일명** | `YYMMDDHHMMss.확장자` (timestamp 기반) |
| **batch_id** | `YYYYMMDD_CATCD_HHMMSS` |
| **shard** | shard_size=1 (현재 실제 설정), 최대 3개 동시 실행 (Semaphore) |
| **코드 테이블 캐시** | handler 실행 단위, TTL 없음, 종료 시 폐기 |
| **global mutable state 금지** | 설계 원칙 |
| **Registry 패턴** | 플랫폼/Stage 이름으로 동적 인스턴스 반환 |

---

## 7. 역사적 의도 복원 (Historical Intent)

과거 대화 요약에서 다음 흐름이 확인됨:

1. **아키텍처 초기화** (a3841622): 모듈형 ETL 아키텍처 확립, Registry 패턴 도입
2. **DiningCode 크롤링 전략 정교화** (e53e2293): HTML 구조 기반 CSS 셀렉터 재작성
3. **PolicyResolver 오류 수정** (d3875c01): `should_retry` → `resolve()` 메서드 이름 불일치
4. **데이터 덮어쓰기 버그 수정** (cfba3326): Stage1에서 고유 파일명 생성 로직 추가
5. **파일 정리** (f0263cf9): 루트 임시 파일 정리

> **현재 코드는 이러한 반복 수정의 결과물이므로, 초기 설계 의도와 실제 코드 간 미세한 불일치 가능성이 있음.**

---

## 8. 문제점 및 위험 요소 (Problems & Risks)

### 🔴 HIGH — 즉각 검증 필요

| # | 위치 | 문제 | 영향 |
|---|------|------|------|
| H1 | `stage4_load.py:37` | `map_category = "CA01"` 하드코딩 | 설계 원칙 위반 (#7장), DI 없이 코드 고정 |
| H2 | `stage4_load.py:83,95` | `category_cd = "IC01"` crawling 적재 하드코딩 | 위와 동일 |
| H3 | `stage4_load.py:117` | `session.commit()` 위치가 `with session.begin_nested()` 외부 | 트랜잭션 경계 모호 - 일부 실패 후 전체 commit 위험 |
| H4 | `constants.py: QUERY_UPSERT_MAP/SHOP` | ON CONFLICT 절 없음 (순수 INSERT) | 중복 실행 시 unique violation, idempotency 없음 |
| H5 | `stage3_validation_normalization.py:31` | `self.code_repo._address_cache` 직접 접근 (private) | 캡슐화 위반, 내부 구조 변경 시 silent breakage |
| H6 | `database.py:44` | `db_manager = DatabaseManager()` 모듈 로드 시 즉시 실행 | import 시 DB 연결 시도 → 환경 없으면 fail |

### 🟡 MEDIUM — 구조적 개선 필요

| # | 위치 | 문제 | 영향 |
|---|------|------|------|
| M1 | `Stage 간 payload` | `Dict[str, Any]`로 전달, Pydantic 없음 | 런타임까지 오류 발견 불가, contract 불명확 |
| M2 | `stage2_handler.py:22-33` | 주석 "리팩토링 필요" — path 수동 구성 | stage execute가 path를 반환하지 않아 handler가 경로를 추측 |
| M3 | `orchestrator.py:25` | `shard_size=1` 고정 하드코딩 | 설계상 shard는 파라미터여야 하는데 magic number |
| M4 | `code_table_repository.py:80` | `code_repo = CodeTableRepository()` 모듈 글로벌 인스턴스 | 설계 원칙(global mutable state 금지)과 잠재적 충돌 |
| M5 | `stage1_raw_collection.py:62` | `reason_code = getattr(e, 'reason_code', ...)` — 일반 Exception도 처리 | BasePipelineException 외 예외는 reason_code 정보 손실 |
| M6 | `diningcode_collector.py:87` | `logger.debug(f"... ({i + 1}) attempts")` — i 변수 loop 종료 후 참조 | 0회 클릭 시 i 미정의 가능성 (루프 한 번도 안 돌면 NameError) |
| M7 | `batch_id 생성` | `YYYYMMDD_CATCD_HHMMSS` 형식 사용 — 설계는 seq(001) 권장 | 실행 시각 중복 시 batch_id 충돌 가능 |
| M8 | `resolver.py:70` | `policy_resolver = PolicyResolver()` 전역 싱글톤 | global mutable state 금지 원칙과 긴장 관계 |

### 🟢 LOW — 미완성 영역

| # | 위치 | 문제 | 영향 |
|---|------|------|------|
| L1 | `naver/google/kakao_collector.py` | 기본 구현만 있음 (discover_stores 없음) | 멀티 플랫폼 지원 불가 |
| L2 | `naver/google/kakao_parser.py` | 스텁 수준 | 위와 동일 |
| L3 | 테스트 없음 | 단위 테스트, 매핑 테스트 전무 | 배포 안전성 불명확 |
| L4 | Metrics 미구현 | phase별 metrics JSONL 없음 | 운영 지표 추적 불가 |
| L5 | retry/reprocess 실행 흐름 미구현 | Stage 5가 JSONL만 기록 — 실제 재시도는 없음 | fail이 ledger에만 쌓이고 재처리 안 됨 |
| L6 | `check_progress.py` 역할 불명확 | 루트에 존재하는 스크립트 | 운영 용도인지 임시용인지 불분명 |
| L7 | `dedup_rule_version = "v1"` | StoreModel에 하드코딩 | 버전 관리 불가 |

---

## 9. 다음 액션 제안 (Next Actions)

> ⚠️ 모든 액션은 이 문서를 기반으로 구현 계획(implementation_plan.md) 수립 후 진행할 것

### 즉시 수정 필요 (설계 원칙 위반 해소)
1. **H1, H2**: `stage4_load.py` hardcoded `category_cd` 제거 → 파라미터로 주입
2. **H3**: 트랜잭션 경계 검토 — `with session.begin_nested()` + 전체 commit 구조 재검토
3. **H4**: `QUERY_UPSERT_MAP/SHOP`에 `ON CONFLICT DO UPDATE` 추가 (idempotency)
4. **H5**: `Stage3`에서 `code_repo._address_cache` 직접 접근 → public 메서드 신설

### 구조적 개선
5. **M1**: Stage 간 payload에 TypedDict 또는 Pydantic 모델 적용
6. **M2**: `stage2_execute()`가 출력 경로를 반환하도록 리팩토링
7. **M6**: `_click_review_more`의 i 변수 참조 버그 수정

### 미완성 영역 구현
8. Naver/Google/Kakao Collector + Parser 구현
9. 테스트 작성 (설계안 24장 기준)
10. Metrics JSONL 파이프라인 구현
11. retry/reprocess 실행 흐름 구현

---

*이 문서는 구현 전 상태 스냅샷이다. 수정 시 반드시 갱신할 것.*
