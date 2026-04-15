# 통합 맛집 데이터 ETL 실행 계획 (PLAN.MD)

본 문서는 `etl/meal` 파이프라인의 **현행 코드 구조와 실행 흐름**을 정리한 실행 계획서입니다.  
`etl/meal/doc/RESEARCH.MD`(코드 분석 보고서)에 근거해, 문서 내 “완료/구현” 표기나 차세대 아키텍처처럼 **분석 근거가 부족하거나 문서 목적을 벗어나는 내용은 제거/정리**했습니다.

---

## 1. 프로젝트 개요 및 전체 흐름 (Overall Workflow)

이 프로젝트는 다이닝코드(DiningCode)에서 **맛집 기본 정보**와 **리뷰(이미지 포함)** 를 수집해 PostgreSQL DB에 적재하는 ETL 파이프라인입니다.

- **배치 실행 스크립트**: `run_batch_pipeline.py`
- **수집 대상 정의**: `targets_example.csv`
- **환경 설정**: `.env` (DB 접속 정보, 카카오 API 키 등)
- **중간 산출물 폴더**: `data/`, `review_data/` (CSV/JSON/이미지 등)

---

## 2. 트랙별 실행 단계 (Component Deep-dive)

### 2-1. 맛집 기본 정보 트랙 (`meal_detail/`)

#### (1) 링크 수집: `01_collect_store_links.py`
- `targets_example.csv` 기반으로 검색 결과 목록에서 가게 상세 페이지 URL을 수집
- 결과는 `data/shop_candidates.csv` 등으로 저장

#### (2) 상세 정보 수집: `02_collect_store_details.py`
- 가게명/주소/평점/메뉴(JSON 형태) 등을 스크래핑
- 결과는 `data/raw_store_data.csv` 등으로 저장

#### (3) 전처리 및 업로드: `03_preprocess_and_upload.py`
- `codeT.csv` 기반으로 행정구역/카테고리 코드 매핑
- 주소 기반 **카카오 API** 호출로 위경도 보정
- `maps → shop → menu` 순으로 데이터 적재
- 적재 성공 시 로컬 임시 파일 정리(Cleanup)

### 2-2. 리뷰/이미지 트랙 (`meal_review/`)

#### (1) 리뷰 스크래핑: `02_collect_store_reviews.py`
- `raw_store_data.csv` 기반으로 리뷰 본문/평점/키워드 수집
- 리뷰 이미지를 다운로드하여 `review_data/images/{가게명}/` 저장
- 텍스트 데이터는 `review_data/jsons/` 등에 저장

#### (2) 리뷰 업로드: `03_preprocess_and_upload_reviews.py`
- JSON 파일을 읽어 DB의 `shop_id`와 매핑
- `posts` 테이블에 리뷰 본문, `images` 테이블에 이미지 경로를 적재
- 적재 성공 시 로컬 JSON/중간 CSV 정리(Cleanup)

---

## 3. DB 테이블 매핑(요약)
`RESEARCH.MD` 기준으로 주요 테이블은 아래와 같습니다.

- **codeT**: 분류 코드(업종 카테고리/지역 코드 등)
- **maps**: 장소 물리 정보(가게명/상세 주소/위경도)
- **shop**: `maps`와 연결되는 가게 엔티티(업종/평점 등)
- **menu**: `shop_id` FK로 메뉴/가격 저장
- **users**: 리뷰 작성자(크롤링 계정 `crawler_bot` 등)
- **posts**: 리뷰 본문 저장(가게/위치 참조)
- **images**: 리뷰 이미지 저장(`table_name`, `table_id`로 게시물과 연결)

---

## 4. 실행 방법
- **전체 배치 실행**: `python run_batch_pipeline.py --targets targets_example.csv --headful`

---

## 5. 데이터 보관 및 보안 메모 (Data Retention & Security)
- **Git 추적 제외(권장)**: `data/`, `review_data/` 등 수집 데이터 및 개인정보가 포함될 수 있는 파일은 저장소 추적에서 제외되도록 `.gitignore`를 강화
- **Auto Cleanup(현행 동작)**: 업로드 성공 시 로컬의 대용량 임시 파일(CSV/JSON)을 정리하는 흐름이 포함될 수 있음

---

## 6. (To-be) images 매핑 검증 설계 메모
`RESEARCH.MD`에 정리된 검증 아이디어를 문서에 남깁니다. (구현은 포함하지 않음)

1. **table_name 유효성 검사**: `images.table_name` 값이 허용된 테이블인지 확인
2. **table_id 실존 여부 검사**: `table_name`이 가리키는 테이블에서 `table_id`(PK)가 존재하는지 확인
3. **삽입 정책 결정**: 실패 시 스킵/에러 로그 등 처리 기준 확정