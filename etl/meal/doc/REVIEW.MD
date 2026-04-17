# [SK-Connect] 프로젝트 아키텍처 및 ETL 운영 가이드 (REVIEW.MD)

본 문서는 `project-understanding` 프레임워크를 기반으로 식당 추천 시스템의 ETL 파이프라인 구조와 반드시 준수해야 하는 운영 규칙을 정리합니다.

---

## 1. 프로젝트 개요 (Project Overview)

*   **목적**: 다이닝코드 기반 식당 상세 정보 및 리뷰 데이터를 수집하고, 정제하여 서비스 DB(PostgreSQL) 및 데이터 레이크(Hive-style)에 적재합니다.
*   **핵심 철학**: 
    *   **모듈화**: 기능별 레이어(Core, Extractor, Transformer, Loader)의 엄격한 분리.
    *   **무결성**: 검증되지 않은 데이터는 적재하지 않으며, 실패 시 원인 추적이 가능해야 함.
    *   **규약**: 정해진 경로 구조와 명칭을 0.1%의 오차도 없이 준수함.

---

## 2. 시스템 아키텍처 (System Architecture)

### 가. 레이어별 역할 (Layer Responsibilities)
| 레이어 | 위치 | 역할 |
| :--- | :--- | :--- |
| **Core** | `src/core/` | 브라우저 제어(Playwright), DB 커넥션, 하이브 경로 관리, 공통 상수. |
| **Extractor** | `src/extractors/` | 웹 사이트 DOM 분석 및 Raw 데이터 추출 (DiningCode 전문). |
| **Transformer** | `src/transformers/` | 데이터 정제, 코드 매핑(카테고리/지역), 포맷 변환. |
| **Loader** | `src/loaders/` | **[핵심]** 하이브 방식 파일 저장 및 DB 연동 적재 수행. |
| **Entry Point** | `run.py` | 배치 실행 인터페이스 (CLI). |

---

## 3. 상세 데이터 흐름 (Detailed Data Flow)

파이프라인은 다음의 **6단계(Stage)**를 거쳐 실행됩니다.

1.  **Extract (수집)**: `LinkExtractor` -> `DiningCodeExtractor` 순으로 실행되어 메모리에 전처리 전 `DataFrame` 형성.
2.  **Save Raw (원본 보존)**: 수집 직후의 데이터를 `process=raw` 경로에 즉시 CSV로 저장.
3.  **Transform (변환)**: `Processor`를 통해 카테고리 코드 변환, 주소 정규화 등 수행.
4.  **Save Cleansing (정제 보존)**: 변환이 완료된 데이터를 `process=cleansing` 경로에 저장.
5.  **Load DB (적재)**: `Loader`가 트랜잭션을 사용하여 DB(maps, shop, crawling 등)에 데이터 삽입.
6.  **Save Final (성공 기록)**: DB 적재까지 완벽히 성공한 결과물을 `process=save` 경로에 저장하여 최종 증거로 남김.

---

## 4. 반드시 준수해야 하는 운영 규칙 (Mandatory Rules)

### 규칙 1: 하이브 스타일 디렉토리 구조 (Rule 3)
모든 데이터는 아래 구조를 0.1%의 오차 없이 따라야 합니다.
`process={step}/service={domain}/year={YYYY}/month={MM}/day={DD}/status={success|fail}/{timestamp}.csv`

### 규칙 2: 로더의 책임 분리 (Rule 5)
*   **오케스트레이터**: 흐름(순서)만 제어합니다.
*   **로더**: 내부에서 **"파일 저장 정책(Hive) + DB 적재"** 두 가지 책임을 모두 완수해야 합니다. 로더 외부로 파일 저장 로직을 분리하는 것은 금지됩니다.

### 규칙 3: 데이터 유효성 검증 (Validation)
**"수집된 데이터만 저장하는 것이 아니라, 검증된 데이터만 저장합니다."**
다음 조건이 충족되지 않으면 해당 레코드는 `status=fail`로 처리하거나 적재를 중단해야 합니다.
1.  **주소(Address)**: `address_detail`이 비어있으면 안 됩니다.
2.  **좌표(Coordinates)**: 위도/경도가 `0`이거나 추출에 실패하면 안 됩니다.
3.  **메뉴(Menu)**: 최소 1개 이상의 유효한 메뉴 데이터가 존재해야 합니다.
4.  **이미지(Image)**: 식당 상세 또는 리뷰 이미지가 최소 1개 이상 수집되어야 합니다.

---

## 5. 장애 대응 및 디버깅 가이드 (Error Handling)

*   **403 Forbidden**: Headless 차단 시 `BaseCrawler`의 User-Agent 설정과 `slow_mo` 옵션을 조정하십시오.
*   **적재 실패 분석**: `process=save` 폴더에 파일이 없다면 `process=raw/cleansing`를 순차적으로 역추적하여 어느 단계에서 유실되었는지 확인하십시오.
*   **DB 검증**: 적재 후 `SELECT COUNT(*)`와 샘플 조회를 통해 실제 데이터가 테이블에 들어갔는지 반드시 증명해야 합니다.

---

## 6. 디렉토리 맵 (Directory Map)

```text
meal/
├── run.py                 # 통합 실행기
├── src/
│   ├── core/              # 인프라 (BaseCrawler, DBClient, FileManager, Constants)
│   ├── extractors/        # 수집기 (Link, DiningCode, Review)
│   ├── transformers/      # 변환기 (Shop, Review)
│   └── loaders/           # 적재기 (Shop, Review, Post)
├── doc/
│   ├── PLAN.MD            # 프로젝트 계획서
│   ├── MODIFY_RULE.MD     # 수정 시 필수 준수 사항
│   ├── ERROR.MD           # 최신 이슈 및 검증 요구사항
│   └── REVIEW.MD          # [본 문서] 전체 흐름 및 운영 가이드
└── tools/
    └── verify_db.py       # DB 적재 수치 검증 툴
```


# 1. 특정 타겟 리스트(CSV)를 기준으로 전체 수집 및 적재 실행
python run.py --targets targets_verify.csv

# 2. 테스트를 위해 수집 개수를 제한하고 싶을 때 (예: 5개만)
python run.py --targets targets_verify.csv --limit 5

# 3. 브라우저가 뜨는 것을 보고 싶을 때 (디버깅용)
python run.py --targets targets_verify.csv --headful


---
**최종 업데이트**: 2026-04-17
**담당**: Antigravity AI Assistant
