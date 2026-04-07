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

## 실행 순서

### 1. 가게 URL 수집
```bash
python 01_collect_store_links.py --targets targets_example.csv --output shop_candidates.csv --max-pages 3 --headful
```

### 2. 상세 데이터 수집
```bash
python 02_collect_store_details.py --input shop_candidates.csv --output raw_store_data.csv --headful
```

### 3. 전처리 및 업로드
```bash
python 03_preprocess_and_upload.py --input raw_store_data.csv --output-dir clean_output --host localhost --port 5432 --dbname mydb --user myuser --password mypw --truncate-first
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
- maps 테이블의 latitude/longitude는 반드시 존재해야 함

---

## 추천 전략
- 서울 / 지역 단위로 수집
- 카테고리 (한식, 카페 등) 분리
- 중복 URL 제거 필수

---

## 한 줄 요약
"검색하지 말고, 목록에서 직접 들어가라"
