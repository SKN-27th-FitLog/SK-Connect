# [Next-Gen] 맛집 데이터 ETL 프로젝트 리뷰 (REVIEW.MD)

본 문서는 리팩토링이 완료된 통합 맛집 데이터 ETL 프로젝트의 기본 설치, 환경 설정 및 데이터 처리 흐름에 대한 종합 가이드입니다.

---

## 1. 프로젝트 개요 (Overview)

이 프로젝트는 다이닝코드(DiningCode)를 포함한 외부 맛집 서비스로부터 데이터를 수집하고, 이를 정제하여 서비스 가용성이 높은 데이터베이스에 적재하는 ETL(Extract, Transform, Load) 파이프라인입니다.

**차세대 아키텍처(Next-Gen)**의 핵심은 수집된 데이터를 즉시 서비스 테이블에 반영하지 않고, **데이터 레이크(Data Lake)**와 **crawling(TC10) 테이블**에 일차적으로 적재하여 데이터 가시성과 검증 가능성을 확보하는 데 있습니다.

---

## 2. 환경 설정 (Environment Setup)

### 2-1. 기본 요구사항
- **Python**: 3.9 이상 권장
- **Database**: PostgreSQL
- **Browser Automation**: Playwright (sync-api)

### 2-2. 의존성 설치
```bash
# 가상환경 활성화 후 실행
pip install -r requirements.txt
playwright install chromium
```

### 2-3. 환경 변수 (`.env`) 설정
프로젝트 루트에 `.env` 파일을 생성하고 다음 항목을 입력합니다.
```env
# Database 설정
DB_HOST=your_host
DB_PORT=5432
SERVICE_DB_NAME=service
DB_USER=your_user
DB_PASSWORD=your_password

# API 설정
KAKAO_API_KEY=your_kakao_rest_api_key

# 실행 설정
TARGETS_FILE=targets_example.csv
```

---

## 3. 차세대 데이터 관리 아키텍처 (Architecture)

### 3-1. 하이브 스타일 데이터 레이크 (Hive-style Partitioning)
모든 정제된 데이터는 로컬 디렉토리에 Hive 스타일의 파티셔닝 구조로 분리되어 저장됩니다.
- **경로 구조**: `{process}/{service}/year={YYYY}/month={MM}/day={DD}/status={success|fail}/{HHMMSS}.csv`
- **예시**: `process=cleansing/service=shop/year=2026/month=04/day=14/status=success/203045.csv`
- **이점**: 시간대별/상태별 데이터 추적이 용이하며, 클라우드 환경(S3 등)으로의 이전이 매우 간편합니다.

### 3-2. crawling 테이블 통합 적재
기존의 `posts` 또는 `maps` 테이블에 직접 적재하던 방식에서 벗어나, 모든 원본 데이터는 **`crawling` (TC10)** 테이블로 모입니다.
- **역할**: 수집된 데이터의 '원본 보존 구역(Staging)' 역할을 수행합니다.
- **스키마 주요 항목**:
    - `title`: 식당명 또는 리뷰 제목
    - `content`: 상세 메뉴 정보 또는 리뷰 본문
    - `thread`: 데이터 도메인 구분 (`shop` 또는 `review`)
    - `article_url`: 수집 출처 URL
    - `map_id` / `category_cd`: 메타데이터 및 카테고리 정보

---

## 4. 실행 가이드 (Execution Guide)

### 4-1. 전체 파이프라인 실행
`run_batch_pipeline.py`를 통해 모든 과정을 순차적으로 자동 실행할 수 있습니다.
```bash
python run_batch_pipeline.py --targets targets_example.csv --headful
```

### 4-2. 주요 실행 스텝
1.  **링크 수집**: 검색 페이지에서 대상 식당의 상세 페이지 URL을 확보합니다.
2.  **상세 수집**: 각 식당의 메뉴, 평점, 주소 등을 크롤링합니다.
3.  **데이터 적재**: 정제된 데이터를 데이터 레이크에 CSV로 저장하고, DB `crawling` 테이블에 입성시킵니다.
4.  **리뷰 수집**: 해당 식당들의 리뷰와 이미지를 수집하여 동일하게 `crawling` 테이블에 적재합니다.

---

## 5. 개발 표준 (Coding Standards)

본 프로젝트의 모든 소스 코드는 다음의 **전문가 품질 표준**을 준수합니다.

- **한국어 상세 주석**: 모든 함수와 복합 로직에는 한국어로 상세한 설명을 달아 가독성을 높였습니다.
- **No Hardcoding**: 모든 시점 정보와 경로는 환경 변수 및 인자(args)를 통해 동적으로 관리합니다.
- **Early Return**: 불필요한 중첩 분기(`else`)를 지양하고 예외 처리를 우선하여 로직이 명확합니다.
- **Extreme Modularization**: 각 기능은 독립적인 함수와 모듈로 분리되어 테스트 및 재사용이 용이합니다.

---
**REVIEW 종료**: 차세대 ETL 파이프라인 세팅이 완료되었습니다. 이제 데이터 적재 후 검증 파이프라인을 통해 서비스 데이터로 전환하는 후속 작업을 진행할 수 있습니다.
