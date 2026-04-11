# meal 디렉토리 분석 보고서 (RESEARCH.MD)

본 보고서는 `c:\dev\Study\meal` 폴더 내의 맛집 정보 및 리뷰 수집 ETL(Extract, Transform, Load) 파이프라인에 대한 상세 분석 결과입니다.

## 1. 프로젝트 개요
이 시스템은 **다이닝코드(DiningCode)** 사이트에서 특정 지역 및 카테고리의 맛집 정보와 관련 리뷰(이미지 포함)를 자동으로 수집하여 **PostgreSQL** 데이터베이스에 저장하는 자동화 파이프라인입니다.

## 2. 전체 디렉토리 구조 및 역할
- `meal/` (Root)
    - `run_batch_pipeline.py`: 전체 프로세스를 총괄하는 배치 실행 스크립트.
    - `targets_example.csv`: 수집 대상 지역과 카테고리 정의 파일.
    - `.env`: 데이터베이스 접속 정보 및 카카오 API 키 등 설정 파일.
    - `meal_detail/`: 맛집 기본 정보 수집 및 DB 업로드 로직.
    - `meal_review/`: 리뷰 데이터 및 이미지 수집, DB 업로드 로직.
    - `data/`, `review_data/`: 수집 과정에서 생성되는 임시 CSV, JSON, 이미지 저장 폴더.

## 3. 상세 동작 프로세스

### 단계 1: 맛집 기본 정보 수집 (`meal_detail/`)
1.  **링크 수집 (`01_collect_store_links.py`)**:
    - `targets_example.csv`를 읽어 해당 지역/카테고리의 검색 결과 목록에서 가게 상세 페이지 URL을 추출합니다.
    - Playwright를 사용하여 동적 페이지를 처리하며, `data/shop_candidates.csv`에 저장합니다.
2.  **상세 정보 추출 (`02_collect_store_details.py`)**:
    - 수집된 URL에 각각 접속하여 가게 이름, 주소, 평점, 메뉴(JSON 형태) 등을 스크래핑합니다.
    - 결과는 `data/raw_store_data.csv`에 저장됩니다.
3.  **전처리 및 DB 업로드 (`03_preprocess_and_upload.py`)**:
    - `codeT.csv`를 참조하여 행정구역 및 카테고리 코드를 매핑합니다.
    - **카카오 API**를 호출하여 주소를 기반으로 위도/경도 좌표를 보정합니다.
    - `maps`, `shop`, `menu` 테이블에 데이터를 삽입한 후, **로컬의 임시 CSV 파일들을 자동으로 삭제(Cleanup)** 합니다.

### 단계 2: 리뷰 및 이미지 수집 (`meal_review/`)
1.  **리뷰 스크래핑 (`02_collect_store_reviews.py`)**:
    - 앞 단계의 `raw_store_data.csv`를 기반으로 각 가게의 리뷰 본문, 평점, 키워드를 수집합니다.
    - 리뷰에 포함된 이미지를 원본 해상도로 다운로드하여 `review_data/images/{가게명}/` 폴더에 저장합니다.
    - 텍스트 데이터는 가게별로 `review_data/jsons/`에 저장됩니다.
2.  **리뷰 데이터 업로드 (`03_preprocess_and_upload_reviews.py`)**:
    - JSON 파일을 읽어 DB의 `shop_id`와 매핑합니다.
    - `posts` 테이블에 리뷰 내용을, `images` 테이블에 이미지 경로를 각각 저장합니다.
    - 작업 완료 후 **로컬의 JSON 및 중간 CSV 파일을 자동으로 정리**합니다.

## 4. 데이터베이스 및 스키마 매핑 상세
수집된 데이터는 아래의 테이블 구조에 따라 정교하게 매핑되어 저장됩니다.

### 데이터베이스 테이블 구성
- **codeT**: 분류 코드 관리 (업종 카테고리, 지역 코드 등). 모든 테이블의 `category_cd`, `address_cd` 등의 기준이 됩니다.
- **maps**: 장소의 물리적 정보 통합 관리. 가게 이름, 상세 주소 및 보정된 위경도 좌표가 저장됩니다.
- **shop**: `maps` 테이블과 1:1 또는 N:1로 연결되며, 상세 업종(한식, 중식 등)과 크롤링된 평점이 관리됩니다.
- **menu**: `shop_id`를 외래 키로 참조하며, 각 가게의 메뉴 이름과 가격 정보를 저장합니다.
- **users**: 리뷰 작성자 관리. 크롤링 데이터는 시스템 내의 `crawler_bot` 계정으로 통합 관리됩니다.
- **posts**: 리뷰 본문 데이터 저장. `shop_id`와 `map_id`를 모두 참조하여 위치 및 가게 정보와 연결됩니다. 평점과 키워드가 본문에 포함되어 저장됩니다.
- **images**: 리뷰에 포함된 이미지 정보 저장. `table_name`('posts')과 `table_id`(post_id)를 통해 해당 리뷰와 물리적으로 연결됩니다.

### 스크립트별 데이터 매핑 전략
- **meal_detail/03_...**: 
    - `maps` -> `shop` -> `menu` 순서로 상위 테이블부터 순차적으로 데이터를 삽입합니다.
    - `address_cd`를 통해 지역별 대분류를 수행하며, Kakao API로 `latitude`, `longitude`를 필수적으로 채웁니다.
- **meal_review/03_...**: 
    - `users` 테이블에서 `crawler_bot` 존재 여부를 확인하고 없으면 자동 생성합니다.
    - `posts` 테이블에 리뷰를 삽입하고 생성된 `post_id`를 기반으로 `images` 테이블에 수집된 이미지 경로를 매핑합니다.

## 5. 핵심 기술 및 특징
- **브라우저 자동화 (Playwright)**: '더보기' 버튼 클릭, 무한 스크롤, 광고 차단 등을 통해 안정적인 데이터 수집을 수행합니다.
- **데이터 정합성 보장**: 외래 키(`REFERENCES`) 제약 조건을 준수하기 위해 상위 테이블 데이터 존재 여부를 확인한 후 삽입을 진행합니다.
- **이미지 및 URL 관리**: 수집된 이미지는 로컬 서버에 저장되며, DB에는 접근 가능한 상대 경로(URL)가 저장되어 백엔드 서비스에서 즉시 활용 가능합니다.
- **자동 관리 (Auto Cleanup)**: DB 업로드가 성공(Commit)하면 로컬의 대용량 임시 파일(CSV, JSON)을 즉시 삭제하여 저장 공간을 최적화합니다.

## 6. 실행 방법 (Batch)
가장 상위 폴더에서 아래 명령어를 통해 전체 파이프라인을 한 번에 구동할 수 있습니다.
```bash
python run_batch_pipeline.py --targets targets_example.csv --headful
```
*(기타 DB 정보 및 API 키는 .env 파일에 설정된 값을 자동으로 참조합니다.)*

## 7. 향후 개선 및 검증 로직 설계 (To-be)
이미지 데이터의 무결성을 보장하기 위해 `images` 테이블 삽입 전 다음과 같은 정밀 검증 로직이 필요합니다.

### 이미지 매핑 검증 프로세스
1. **table_name 유효성 검사**:
    - `images` 테이블의 `table_name` 컬럼에 입력될 값이 `codeT` 테이블에 새롭게 정의된 '테이블 코드' 그룹에 속하는지 확인합니다.
    - 예: `SELECT 1 FROM codeT WHERE cd_upper = 'TG01' AND name = [입력된 table_name]` (TG01이 테이블 그룹 코드인 경우)
2. **table_id 실존 여부 검사 (Dynamic Cross-check)**:
    - `table_name`이 유효하다면, 해당 테이블(예: `posts`)에서 `table_id`가 실제 기본 키(PK)로 존재하는지 동적 쿼리를 통해 확인합니다.
    - 예: `table_name`이 'posts'인 경우 -> `SELECT 1 FROM posts WHERE post_id = [입력된 table_id]`
3. **삽입 제약**:
    - 위 두 가지 검증을 모두 통과한 데이터만 `images` 테이블에 삽입하며, 실패 시 에러 로그를 남기고 해당 이미지 레코드를 무시하거나 예외 처리합니다.

## 8. 실행 방법 (Batch)
가장 상위 폴더에서 아래 명령어를 통해 전체 파이프라인을 한 번에 구동할 수 있습니다.
```bash
python run_batch_pipeline.py --targets targets_example.csv --headful
```
*(기타 DB 정보 및 API 키는 .env 파일에 설정된 값을 자동으로 참조합니다.)*

