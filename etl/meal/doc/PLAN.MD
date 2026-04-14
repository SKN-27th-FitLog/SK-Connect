# 통합 맛집 데이터 ETL 프로젝트 상세 실행 계획 (PLAN.MD)

본 문서는 `c:\dev\Study\meal` 프로젝트의 전체 구조, 동작 원리 및 향후 검증 로직 추가를 위한 종합 가이드라인입니다. 누구나 쉽게 이해할 수 있도록 실제 코드베이스를 기반으로 꼼꼼하게 정리하였습니다.

---

## 1. 프로젝트 전체 흐름 (Overall Workflow)

이 프로젝트는 **식당 정보 수집 → 위경도 보정 → 리뷰 및 이미지 수집 → DB 저장**의 4단계로 구성된 파이프라인입니다. `run_batch_pipeline.py`가 지휘자 역할을 하여 모든 과정을 순차적으로 실행합니다.

---

## 2. 파일별 상세 기능 및 구현 방식 (Component Deep-dive)

### [Part 1] 맛집 상세 정보 파이프라인 (`meal_detail/`)

#### 1-1. 링크 수집: `01_collect_store_links.py` [Legacy]
- 다이닝코드 검색 목록에서 상세 페이지 URL 수집. (현재 `raw/collect_links.py`로 대체됨)

#### 1-2. 상세 정보 추출: `02_collect_store_details.py` [Legacy]
- 메뉴, 가격, 평정 등 상세 데이터 추출. (현재 `raw/collect_details.py`로 대체됨)

#### 1-3. 전처리 및 업로드: `03_preprocess_and_upload.py` [Legacy]
- `[x]` **상수 Enum 적용**: Category, FoodCategory, Location Enum 도입 완료.
- `[x]` **공통 유틸리티 적용**: `common_utils` 통합 완료.

---

## 3. [전략적 설계] 데이터 정합성 및 고도화 전략 (완료)

- `[x]` **중복 방지**: 가게(좌표/정규화), 메뉴, 리뷰(해시) 중복 체크 구현 완료.
- `[x]` **트랜잭션**: 모든 업로드 과정에 원자성 보장(`ROLLBACK`) 적용 완료.
- `[x]` **아카이빙**: 성공 시 `archives/` 폴더 이동 보존 정책 적용 완료.

---

## 4. [추가] 코드 재사용성 및 구조 개선 (Refactoring)
- `[x]` **공통 유틸리티 모듈(`common_utils.py`) 생성**: 중복 로직 통합 관리 완료.
- `[x]` **기존 스크립트 리팩토링**: `03` 계열 스크립트 유틸리티 적용 완료.

---

## 5. [추가] 상수 관리 효율화 (members.py & Enum)
- `[x]` **상수 관리 파일(`members.py`) 생성**: 시스템 코드 Enum 구조화 완료.
-     - `Status`, `PostType`, `Category`, `FoodCategory`, `Location`, `TablePrefix`
- `[x]` **기존 스크립트 상수 치환**:
-     - `[x]` `meal_detail/03_preprocess_and_upload.py` 적용 완료
-     - `[x]` `meal_review/03_preprocess_and_upload_reviews.py` 적용 완료
-     - `[x]` `common_utils.py` 적용 완료

---

## 6. 실행 및 환경 가이드

- **전체 배치 실행**: `python run_batch_pipeline.py --targets targets_example.csv --headful`
- **유지보수**: `data/archives/` 및 `review_data/archives/` 폴더를 주기적으로 관리하십시오.

---

## 7. [긴급] 리뷰 데이터 매핑 정합성 해결 (Fix: Review Address Mapping)
- **현상**: 수집된 509건 중 3건만 업로드됨 (주소 불일치로 인한 매핑 실패).
- **원인**: CSV의 전체 주소(Full Address)와 DB의 상세 주소(Detail Address)를 직접 비교하여 매핑이 누락됨.
- **해결 방안 (차세대 검증 파이프라인에서 처리 예정)**: 
    - [ ] **Address Detail Suffix Match**: DB의 상세 주소가 CSV의 전체 주소 끝부분에 포함되어 있는지 확인하는 유연한 매핑 로직 도입.
    - [ ] **Store Name Normalization**: 가게 이름에서 특수문자 및 공백을 제거하여 정합성 강화.

---

## 8. [향후] 데이터 보관 및 보안 정책 (Data Retention & Security)
- [ ] **Git 추적 제외**: `data/`, `review_data/` 등 수집 데이터 및 개인정보가 포함된 파일이 Git 저장소에 올라가지 않도록 `.gitignore` 설정 강화.
- [x] **자동 삭제(Auto-Cleanup)**: DB 업로드 성공 시 로컬 JSON 및 임시 CSV 파일을 삭제하여 보안성 및 저장 공간 효율성 증대.
- [x] **삭제 이력 요약(Cleanup Summary)**: 삭제된 데이터의 파일명, 처리 시각, 처리 건수를 기록한 별도의 리포트 파일을 생성하여 추후 정합성 검증 및 이력 관리 용도로 활용.

---

## 9. [차세대] AWS Lambda & 데이터 레이크 아키텍처 (Next-Gen Architecture)

기존 파이프라인을 AWS Lambda 및 클라우드 네이티브 환경에 최적화하고, 데이터 관리의 투명성을 높이기 위한 고도화 설계입니다.

### [구현 상태 요약]
| 기능 구분 | 주요 내용 | 상태 | 비고 |
| :--- | :--- | :---: | :--- |
| **데이터 저장** | crawling (TC10) 테이블 전환 | `[x]` | 03_preprocess_... 반영 완료 |
| **데이터 레이크** | Hive Style 계층적 폴더 구조 | `[x]` | get_hive_path() 구현 완료 |
| **품질 표준** | 한국어 주석 및 클린 코드 | `[x]` | 전 모듈 적용 완료 |
| **환경 격리** | `raw/clean/save` 및 `requirements.txt` | `[x]` | 단계별 폴더 및 독립 환경 구축 완료 |
| **품질 표준** | Any/Unknown 타입 금지 (엄격한 타입) | `[x]` | 전 모듈 Type Hinting 완료 |
| **품질 표준** | `print()` 제거 및 `logging` 도입 | `[x]` | 전 모듈 적용 완료 |

### 9-1. 데이터 저장 전략 변경 (Review Storage Pivot)
- [x] **리뷰 데이터 적재 대상 변경**: 기존 `posts` 테이블에 직접 저장하던 방식을 중단하고, 모든 수집 데이터는 일차적으로 `crawling` (TC10) 테이블에 저장합니다.
- [ ] **검증 파이프라인 도입**: `crawling` 테이블에 저장된 데이터를 기반으로 자동 생성 파이프라인(Validation Pipeline)을 실행하여 정합성이 검증된 데이터만 최종 서비스 테이블로 이동시킵니다.

### 9-2. 하이브 스타일 데이터 레이크 구조 (Hive-style Partitioning)
- [x] **계층 구조 도입**: 데이터의 생명주기를 명확히 관리하고 쿼리 효율성을 높이기 위해 `item=value` 형식의 계층적 디렉토리 구조를 도입합니다.
- **기본 경로 구조**: `{process}/{service}/year={YYYY}/month={MM}/day={DD}/status={success|fail}/{HHMMSS}.csv`
- **프로세스 정의 (`process`)**:
    - `process=raw`: 수집 직후의 원본 데이터
    - `process=cleansing`: 정제 및 전처리가 완료된 데이터
    - `process=save`: DB 적재 준비가 완료된 최종 데이터

### 9-3. 위경도(Geospatial) 데이터 강화
- [ ] **정밀 좌표 수집**: 상세 페이지 내 지도 API 연동 또는 Naver/Kakao Maps 크롤링을 통해 누락 없는 위도/경도 데이터를 확보합니다.
- [ ] **위치 기반 서비스 최적화**: 주소 기반 역지오코딩의 한계를 보완하여 정밀한 위치 기반 추천 및 검색 기능을 지원합니다.

### 9-4. 설계 원칙 및 복구 전략 (Resilience & Clean Code)
- [x] **자율 복구(Self-Healing)**: 특정 날짜의 `status=success` 데이터가 존재하지 않을 경우, 해당 시점을 자동으로 탐지하여 재수집을 트리거하는 스케줄러 로직을 구현합니다.
- [x] **Lambda-Native 설계 (단계별 환경 격리)**: 
    - **디렉토리 계층화 완료**: `meal_detail/`, `meal_review/` 산하에 `raw/`, `clean/`, `save/` 폴더를 구축하여 데이터 흐름에 따른 물리적 격리를 완료했습니다.
    - **의존성 개별 관리 완료**: 각 폴더의 `requirements.txt`를 통해 람다 배포 및 독립 실행 환경을 최적화했습니다.
- **코드 품질 표준 (Professional Standards)**:
    - [x] **Strict Typing**: `Any` 또는 `UNKNOWN` 타입을 배제하고 명확한 Type Hinting을 적용하여 코드의 안정성을 확보했습니다.
    - [x] **Logging Standard**: `print()`를 전면 제거하고 표준 `logging` 모듈을 도입하여 로그 수준별 관리를 수행합니다.
    - [x] **SDK-Style Utils**: `common_utils.py`를 호출자(Script)가 아닌 규격(SDK) 중심으로 재설계하여 인터페이스 일관성을 확보했습니다.

---

## 10. [추가] 위경도 정밀 크롤링 시스템 (`meal_geospatial/`)

데이터의 정합성을 높이기 위해 주소 기반 좌표의 한계를 넘는 정밀 크롤링 모듈을 추가할 예정입니다.

- **표준 구조 준수**: `meal_detail/` 등과 동일하게 `raw/`, `clean/`, `save/` 구조 및 `requirements.txt` 격리를 적용합니다.
- **기능**: 지도 서비스(Naver/Kakao)의 상세 페이지를 직접 탐색하여 정확한 위경도 좌표를 추출합니다.

---

## 11. 차세대 아키텍처 파일 구조 (Project Structure)

```text
etl/meal/
├── common_utils.py       # SDK형 공통 유틸리티 (Strict Typing)
├── members.py            # 시스템 공통 상수/Enum (Strict Typing)
├── run_batch_pipeline.py # 통합 배치 오케스트레이터
├── targets_example.csv   # 수집 대상 목록 샘플
├── meal_detail/          # [맛집 상세 모듈]
│   ├── raw/              # 데이터 수집 (playwright)
│   ├── clean/            # 데이터 전처리 (pandas)
│   └── save/             # DB 적재 (psycopg2)
└── meal_review/          # [맛집 리뷰 모듈]
    ├── raw/              # 데이터 수집 (playwright)
    ├── clean/            # 데이터 전처리 (pandas)
    └── save/             # DB 적재 (psycopg2)
```

---
**보고서 종료**: 차세대 아키텍처 마이그레이션이 성공적으로 완료되었습니다. 모든 모듈에 대해 엄격한 타입 가이드라인과 단계별 격리 구조가 적용되었으며, 향후 검증 파이프라인 및 정밀 위경도 크롤링 모듈 확장이 용이한 상태입니다.