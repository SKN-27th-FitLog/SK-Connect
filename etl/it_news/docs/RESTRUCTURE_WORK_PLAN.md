# IT News ETL 재구성 사전 계획

## 기준
- 최우선 문서: `etl/it_news/docs/PLAN.md`
- 작업 범위: `etl/it_news` 내부만 재구성
- 참고 구현: `01_getter_threads`, `02_cleaning_tables`, `03_insert_tables`, `update_db_it_news.py`

## 목표
- ETL 흐름을 `crawling -> cleaning -> save` 3단계로 재정리한다.
- 단계별로 `common` 폴더와 `requirements.txt`를 둔다.
- 날짜별 `success` / `fail` 폴더만 봐도 실행 결과를 확인할 수 있게 한다.
- `crawling` 테이블 적재까지 자동화하고, `comments` DB 적재는 이번 범위에서 제외한다.

## 구현 방침
1. 기존 사이트별 크롤러는 최대한 재사용하고 새 단계 러너가 감싼다.
2. 수집 성공 파일은 `crawling/raw/YYYY/MM/DD/success`, 실패 파일은 `.../fail`로 분리한다.
3. 클리닝은 DB 스키마에 맞는 컬럼으로 표준화하고, 실패 행은 별도 CSV로 분리한다.
4. 저장은 `cleaning` 성공 파일만 읽고 `crawling` 테이블에 insert 한다.
5. 실행 전후 기록은 `docs` 아래 별도 문서로 남긴다.

## 제외 항목
- `comments` 테이블 insert
- `images` 테이블 insert
- 기존 레거시 스크립트 삭제 또는 대규모 이동
