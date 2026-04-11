# 통합 맛집 데이터 ETL 프로젝트 상세 실행 계획 (PLAN.MD)

본 문서는 `c:\dev\Study\meal` 프로젝트의 전체 구조, 동작 원리 및 향후 검증 로직 추가를 위한 종합 가이드라인입니다. 누구나 쉽게 이해할 수 있도록 실제 코드베이스를 기반으로 꼼꼼하게 정리하였습니다.

---

## 1. 프로젝트 전체 흐름 (Overall Workflow)

이 프로젝트는 **식당 정보 수집 → 위경도 보정 → 리뷰 및 이미지 수집 → DB 저장**의 4단계로 구성된 파이프라인입니다. `run_batch_pipeline.py`가 지휘자 역할을 하여 모든 과정을 순차적으로 실행합니다.

---

## 2. 파일별 상세 기능 및 구현 방식 (Component Deep-dive)

### [Part 1] 맛집 상세 정보 파이프라인 (`meal_detail/`)

#### 1-1. 링크 수집: `01_collect_store_links.py`
- 다이닝코드 검색 목록에서 상세 페이지 URL 수집.

#### 1-2. 상세 정보 추출: `02_collect_store_details.py`
- 메뉴, 가격, 평정 등 상세 데이터 추출.

#### 1-3. 전처리 및 업로드: `03_preprocess_and_upload.py`
- `[x]` **상수 Enum 적용**: Category, FoodCategory, Location Enum 도입 완료.
- `[x]` **공통 유틸리티 적용**: `common_utils` 통합 완료.

---

### [Part 2] 리뷰 및 이미지 파이프라인 (`meal_review/`)

#### 2-1. 리뷰/이미지 수집: `02_collect_store_reviews.py`
- `[x]` 원본 소스 URL 수집 로직 반영 완료.

#### 2-2. 리뷰 업로드: `03_preprocess_and_upload_reviews.py`
- `[x]` **상수 Enum 적용**: Status, PostType, TablePrefix Enum 도입 완료.
- `[x]` **트랜잭션 강화**: 게시글 및 이미지 통합 처리 완료.

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
    - `Status`, `PostType`, `Category`, `FoodCategory`, `Location`, `TablePrefix`
- `[x]` **기존 스크립트 상수 치환**:
    - `[x]` `meal_detail/03_preprocess_and_upload.py` 적용 완료
    - `[x]` `meal_review/03_preprocess_and_upload_reviews.py` 적용 완료
    - `[x]` `common_utils.py` 적용 완료

---

## 6. 실행 및 환경 가이드

- **전체 배치 실행**: `python run_batch_pipeline.py --targets targets_example.csv`
- **유지보수**: `data/archives/` 및 `review_data/archives/` 폴더를 주기적으로 관리하십시오.

---
**보고서 종료**: 본 계획서의 모든 단계(리팩토링 및 상수 Enum화 포함)가 구현 완료되었습니다. 