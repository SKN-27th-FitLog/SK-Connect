# ETL 파이프라인 운영 및 실행 가이드 (Operating Guide)

이 문서는 다이닝코드(Diningcode) 식당 정보 수집 시스템의 자동화 구조와 운영 방법, 그리고 사이트 구조 변경 시 대응 방안을 설명합니다.

---

## 1. 자동화 구조 (Architecture Overview)

본 프로젝트는 **5단계 스테이지 방식(Stage-based Pipeline)**으로 설계되어 수집부터 DB 적재까지 전 공정이 자동화되어 있습니다.

### [Stage 0] Target Selection (대상 선정)
- **로직**: `TargetSelection` 클래스가 담당합니다. 
- **자동화**: DB의 실패 내역(Retry 대상)을 우선 확보하고, 부족분은 소스 풀(Source Pool)에서 신규 URL을 가져와 일일 목표량(기본 100건)을 채웁니다.

### [Stage 1] Raw Collection (원시 수집)
- **도구**: Playwright 기반의 브라우저 자동화 (`PlaywrightCollector`)를 사용합니다.
- **자동화**: '리뷰 더보기', '메뉴 더보기' 버튼 등을 자동으로 클릭하여 동적 데이터를 모두 확보한 후 HTML 원본을 파일로 보존합니다.

### [Stage 2] Candidate Parsing (후보 파싱)
- **로직**: `StoreParser` 클래스가 HTML에서 필요한 정보(이름, 주소, 메뉴, 리뷰 등)를 추출합니다.
- **유연성**: JSON-LD(구조화 데이터)를 우선 탐색하고, 실패 시 HTML 셀렉터로 Fallback합니다.

### [Stage 3] Validation & Normalization (정규화 및 중복 체크)
- **로직**: 상호명/주소 정규화를 수행한 후 `DedupService`를 통해 이미 DB에 존재하는 식당인지 판별합니다.

### [Stage 4] Database Sync (DB 적재)
- **로직**: `DatabaseSync`와 `StoreRepository`가 한 번의 트랜잭션으로 **4개 테이블(Shop, Menu, Review, Image)**에 데이터를 수집 단계별로 동기화 적재합니다.

---

## 2. 웹사이트 변경 시 대응 방법 (Site Update Handling)

웹사이트의 UI나 구조가 변경되면 다음과 같은 부분을 확인하고 수정해야 합니다.

### A. 수집 단계 (버튼 클릭 등 실패 시)
- **대상 파일**: `src/collectors/playwright_collector.py`
- **수정 포인트**: `targets` 리스트에 정의된 '더보기' 버튼의 셀렉터(예: `button:has-text('메뉴 더보기')`)가 변경되었는지 확인합니다.

### B. 파싱 단계 (데이터 추출 실패 시) - **가장 중요**
- **대상 파일**: `src/parsers/store_parser.py`
- **수정 포인트**:
    - `name`, `address` 등을 찾는 BeautifulSoup 셀렉터 (`.tit`, `.addr` 등).
    - 메뉴 블록 셀렉터 (`.menu-info`).
    - 리뷰 블록 셀렉터 (`.latter-graph`, `.person-review`).
- **팁**: 다이닝코드는 JSON-LD 형식을 사용하므로, 사이트 개편 시에도 JSON-LD 구조가 유지된다면 파싱 로직을 크게 수정하지 않아도 데이터를 안정적으로 가져올 수 있습니다.

---

## 3. 실행 가이드 (Execution Guide)

### 환경 설정 (.env)
실행 전 프로젝트 루트의 `.env` 파일에 DB 연결 정보가 정확한지 확인하세요.
```env
DB_HOST=localhost
DB_PORT=5432
SERVICE_DB_NAME=service
DB_USER=user
DB_PASSWORD=password123
```

### 파이프라인 수동 실행 (Full Cycle Demo)
특정 URL에 대해 수집부터 적재까지 테스트하려면 다음 명령어를 실행합니다.
```powershell
python scripts/demo_full_playwright.py --url "수집하려는_다이닝코드_URL"
```

### 자동 배치 실행 (Orchestrator)
일일 목표량을 채우는 자동 배치는 `OrchestratorV4`를 통해 실행됩니다. 

---

## 4. 실패 대응 및 모니터링 (Failure Handling)

파이프라인 실행 중 오류가 발생하면 **Stage 5 (Fail Classification)**가 가동됩니다.
- **분류**: 403 차단(`BLOCK`), 셀렉터 불일치(`UI_CHANGE`), 네트워크 일시 오류(`RETRY`) 등으로 자동 분류됩니다.
- **로그**: `logs/etl_YYYYMMDD.log` 파일에서 상세한 오류 원인을 확인할 수 있습니다.
- **자동 재시도**: `action='retry'`로 분류된 건은 다음날 `Stage 0`에서 자동으로 다시 수집 대상에 포함됩니다.

---

## 5. 유지보수 팁
- **데이터 레이크**: `data_lake/` 폴더 하위에 각 스테이지별 중간 파일이 저장되므로, DB 적재에 문제가 생겼을 때 원본 데이터를 다시 확인할 수 있습니다.
- **단위 테스트**: 로직을 수정한 후에는 `pytest` 명령어를 통해 전체 기능에 이상이 없는지 확인하는 습관을 권장합니다.
