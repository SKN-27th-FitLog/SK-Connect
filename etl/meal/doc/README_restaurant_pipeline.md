# Restaurant Listing Pipeline (README)

## 개요
이 파이프라인은 **CSV 기반 검색 방식이 아니라**
목록 페이지 → 상세 페이지 진입 방식으로 맛집 데이터를 수집합니다.

### 구성
1. 01_collect_store_links.py
   - 지역/카테고리 목록 페이지에서 가게 URL 수집

2. 02_collect_store_details.py
   - 수집된 URL로 상세 페이지 접근 후 데이터 수집

3. 03_preprocess_and_upload.py
   - maps / shop / menu 테이블용 데이터 생성 및 PostgreSQL 업로드

---

## 설치
```bash
pip install pandas playwright psycopg2-binary
playwright install
```

---

## 실행 방법

이제 시스템이 배치(Batch) 스타일로 고도화되어 전체 파이프라인(상세수집+리뷰수집)을 한 번에 실행할 수 있습니다.

```bash
# etl/meal 폴더 최상단에서 실행하세요
python run_batch_pipeline.py \
    --targets "meal_detail/targets_example.csv" \
    --host "DB주소" \
    --dbname "디비명" \
    --user "유저명" \
    --password "암호" \
    --kakao-api-key "카카오REST_API_KEY" \
    --headful

# 개별 실행이 필요한 경우 (예: 링크 수집만)
python meal_detail/01_collect_store_links.py --targets targets_example.csv --headful
```

---

## 핵심 개념

### 기존 방식 (문제점)
- CSV 기반 검색
- 검색 결과 오차 발생
- CSV 없으면 실행 불가

### 개선 방식
- 목록 페이지 기반 크롤링
- 가게 URL 직접 확보
- 상세 페이지 직접 접근
- 더 안정적이고 확장 가능

---

## 주의사항
- LISTING_URL_TEMPLATE는 반드시 실제 사이트 구조에 맞게 수정 필요
- selector (CSS 선택자)는 사이트마다 다르므로 조정 필요
- maps 테이블의 latitude/longitude 보강을 위해 카카오 API 키(`--kakao-api-key`) 설정 사용이 필수로 권장됩니다.
- DB 업로드에 성공하면 로컬에 누적된 `csv`와 `json` 파일들은 보안 및 용량 최적화를 위해 **자동으로 영구 삭제(Clear)** 됩니다.

---

## 추천 전략
- 서울 / 지역 단위로 수집
- 카테고리 (한식, 카페 등) 분리
- 중복 URL 제거 필수

---

## 한 줄 요약
"검색하지 말고, 목록에서 직접 들어가라"
