# 통합 맛집 데이터 ETL 실행 예정 계획 (PLAN.MD - To-be)

본 문서는 `etl/meal` 파이프라인의 **개선된 실행 흐름 및 데이터 정합성 강화 계획**을 정리한 기준 문서입니다.
**AWS 호환성을 위해 기존의 하이브 스타일 경로 구조를 유지**하며, 데이터가 올바른 테이블에 연결되어 저장되도록 설계를 보완합니다.

---

## 1. 프로젝트 주요 개선 목표
1. **데이터 경로 유지**: AWS S3 등과의 연동을 고려하여 **기존 하이브 스타일(process=*/service=*/year=*/...) 경로 구조를 강하게 유지**함
2. **정밀한 DB 매핑**: 데이터 성격에 따라 `maps`, `shop`, `menu`, `crawling` 테이블로 분산 적재 및 FK 연결
3. **카카오 위경도 연동**: 모든 가게에 대해 카카오 REST API를 호출하여 `maps` 테이블의 정확한 좌표 확보
4. **수집 범위 보장**: 누락 없는 전수 수집(Detail & Review)을 위한 예외 처리 및 검증 로직 강화
5. **트랙 분리**: 가게 정보(`service=shop`)와 리뷰 정보(`service=review`)를 명확히 분리하여 관리

---

## 2. 상세 실행 단계 (Workflow)

### 2-1. 맛집 기본 정보 트랙 (`meal_detail/`)

#### (1) 링크 수집: `raw/collect_links.py`
- `targets_example.csv` 기반으로 가게 상세 페이지 URL 확보
- 결과: `process=raw/service=shop/year=*/month=*/day=*/status=success/*.csv`

#### (2) 상세 정보 수집: `raw/collect_details.py`
- 최신 링크 파일을 읽어 가게명, 주소, 평점, 메뉴 데이터 원천 스크래핑
- 결과: `process=raw/service=shop/year=*/month=*/day=*/status=success/*.csv`

#### (3) 데이터 전처리: `clean/preprocess.py`
- `codeT` 참조를 통한 코드 변환 및 데이터 정규화
- 결과: `process=cleansing/service=shop/year=*/month=*/day=*/status=success/*.csv`

#### (4) 장소 및 가게 마스터 적재: `save/upload_shop_to_db.py` **[핵심]**
- **카카오 API**: `store_address`를 기반으로 위경도 변환 수행
- **`maps` 테이블**: 이름, 상세주소, 위경도, 지역코드(`codeT` 참조) 저장
- **`shop` 테이블**: `map_id` 연결, 평점, 가게 카테고리(`codeT` 참조) 저장
- **`menu` 테이블**: `shop_id` 연결, 메뉴명, 가격 정보 저장

#### (5) 통합 게시글 적재: `save/upload_to_db.py`
- `crawling` 테이블에 게시글 형태의 가게 상세 데이터 적재 (`thread='shop'`)
- **결과**: `process=save/service=shop/year=*/month=*/day=*/status=success/*.csv` (적재 성공 내역 저장)

---

### 2-2. 리뷰 데이터 트랙 (`meal_review/`)

#### (1) 전수 리뷰 수집: `raw/collect_reviews.py`
- 상세 정보를 읽어 모든 가게에 대해 리뷰 본문/평점/이미지 수집
- 결과: `process=raw/service=review/year=*/month=*/day=*/status=success/*.csv`
- 리뷰 이미지는 별도 경로(`review_data/images/{가게명}/`)에 저장 가능 (분리 저장)

#### (2) 리뷰 전처리: `clean/preprocess_reviews.py`
- 수집된 리뷰 텍스트 및 날짜 형식을 DB 스키마에 맞게 변환
- 결과: `process=cleansing/service=review/year=*/month=*/day=*/status=success/*.csv`

#### (3) 리뷰 DB 적재: `save/upload_reviews_to_db.py`
- **`crawling` 테이블**: 리뷰 본문, 평점, 작성일 등을 적재 (`thread='review'`)
- **`images` 테이블**: 리뷰 사진 경로 적재 및 해당 게시글과 연결
- **결과**: `process=save/service=review/year=*/month=*/day=*/status=success/*.csv` (적재 성공 내역 저장)

---

## 3. 데이터베이스 정합성 및 연결 구조

- **계층 구조**: `maps(위치)` -> `shop(가게 마스터)` -> `menu(가격)` & `crawling(게시글/리뷰)`
- **테이블 역할**:
    - **`maps`**: 물리적 위치 정보 (중복 방지 핵심)
    - **`shop`**: 서비스용 가게 마스터 정보
    - **`menu`**: 가게별 메뉴 및 가격 정보 (1:N)
    - **`crawling`**: 상세 정보 및 리뷰 텍스트를 통합 관리하는 게시판형 테이블
    - **`codeT`**: 모든 카테고리 및 지역 코드의 표준 소스

---

## 4. 실행 및 사후 검증
- **실행**: `python run_batch_pipeline.py --targets targets_example.csv`
- **검증 항목**:
    - `maps`, `shop` 테이블의 데이터 수가 `raw_store_data`와 일치하는가? - 60개 (완료)
    - `maps` 테이블의 위경도(`latitude`, `longitude`)가 정상적으로 채워졌는가? - (API 키 적용 완료, 재검증 성공)
    - `menu`와 `crawling` 데이터가 각 가게(`shop_id`)에 정확히 연결되었는가? - 60개 (완료)

---

## 5. 주요 개선 및 버그 수정 완료 내역 (Troubleshooting Results)

작업이 완료되어 파이프라인의 안정성과 무결성이 확보되었습니다.

#### (1) 적재 안정성 강화 (Stability) - **완료**
- `upload_shop_to_db.py` 루프 내부 개별 `try-except` 적용: 한 건의 오류가 전체를 멈추지 않음
- `recover_failed_files.py` 유틸리티 추가: `status=fail` 데이터를 자동으로 복구하여 재실행 지원

#### (2) 리뷰 및 이미지 수집 로직 복구 (Review Track Fix) - **완료**
- `collect_reviews.py`: 별점, 날짜, 본문 추출 로직 구현 및 `NameError` 해결
- 이미지 수집 기능 정상화

#### (3) 데이터베이스 매핑 정밀화 (DB Schema Match) - **완료**
- `upload_reviews_to_db.py`: `images` 테이블 스키마 불일치(column mismatch) 해결
- `crawling` 테이블 내 `thread` 필드(shop/review) 구분 적재 확인

#### (4) 환경 설정 자동화 - **완료**
- `run_batch_pipeline.py`에서 `.env` 데이터(KAKAO_API_KEY 등)가 하위 모듈에 누락 없이 전달되도록 수정