# update_db_it_news — 실행 가이드

`update_db_it_news.py`는 IT 뉴스 ETL을 `crawling -> cleaning -> save` 3단계로 순차 실행하는 진입점이다.

## 실행 방법

레포지토리 루트에서:

```bash
python etl/it_news/update_db_it_news.py
```

특정 날짜 폴더를 다시 처리하려면:

```bash
python etl/it_news/update_db_it_news.py --date 2026-04-19
```

## 실행 순서

1. `etl/it_news/crawling/run_crawling.py`
2. `etl/it_news/cleaning/run_cleaning.py`
3. `etl/it_news/save/run_save.py`

모든 단계는 순차 실행이며, 단계 중 하나라도 실패하면 즉시 중단한다.

## 산출물 폴더

### crawling
- 성공: `etl/it_news/crawling/raw/YYYY/MM/DD/success/*.csv`
- 실패: `etl/it_news/crawling/raw/YYYY/MM/DD/fail/*.csv`

### cleaning
- 성공: `etl/it_news/cleaning/cleaning/YYYY/MM/DD/success/*.csv`
- 실패: `etl/it_news/cleaning/cleaning/YYYY/MM/DD/fail/*.csv`

### save
- 성공: `etl/it_news/save/save/YYYY/MM/DD/success/*.csv`
- 실패: `etl/it_news/save/save/YYYY/MM/DD/fail/*.csv`

## 단계별 책임

### crawling
- 기존 `01_getter_threads` 스크립트를 호출해 사이트별 목록/본문 수집을 실행한다.
- 필수값 누락 또는 `state != ok` 행은 fail CSV로 분리한다.

### cleaning
- raw 성공 파일만 읽어 `crawling` 테이블 형식으로 표준화한다.
- DB `MAX(created_at)` 조회가 가능하면 해당 시각 이후 데이터만 남긴다.
- DB 조회가 불가능하면 실행일 기준 3개월 전을 fallback 기준으로 사용한다.

### save
- cleaning 성공 파일만 읽어 PostgreSQL `crawling` 테이블에 insert 한다.
- DB 연결 정보는 `PGHOST`, `PGPORT`, `PGDATABASE`, `PGUSER`, `PGPASSWORD` 또는 기본값을 사용한다.

## 의존성

- `etl/it_news/crawling/requirements.txt`
- `etl/it_news/cleaning/requirements.txt`
- `etl/it_news/save/requirements.txt`

## 참고 문서

- [local-database-setup.md](local-database-setup.md)
- [docs/PLAN.md](docs/PLAN.md)
- [docs/RESTRUCTURE_WORK_PLAN.md](docs/RESTRUCTURE_WORK_PLAN.md)
- [docs/RESTRUCTURE_WORK_RESULT.md](docs/RESTRUCTURE_WORK_RESULT.md)
