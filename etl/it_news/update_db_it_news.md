# update_db_it_news — 실행 가이드

`update_db_it_news.py`는 IT 뉴스 ETL을 `thread` / `comment` 대상별로 순차 실행하는 진입점이다.

## 실행 방법

레포지토리 루트에서:

```bash
python etl/it_news/update_db_it_news.py
```

기본값은 `thread` 파이프라인만 실행한다.

특정 날짜 폴더를 다시 처리하려면:

```bash
python etl/it_news/update_db_it_news.py --date 2026-04-19
```

댓글까지 함께 실행하려면:

```bash
python etl/it_news/update_db_it_news.py --targets thread comment --comment-user-id 1
```

## 실행 순서

### thread
1. `etl/it_news/crawling/run_crawling.py`
2. `etl/it_news/cleaning/run_cleaning.py`
3. `etl/it_news/save/run_save.py`

### comment
1. `etl/it_news/crawling/run_comment_crawling.py`
2. `etl/it_news/cleaning/run_comment_cleaning.py`
3. `etl/it_news/save/run_comment_save.py`

모든 단계는 순차 실행이며, 단계 중 하나라도 실패하면 즉시 중단한다.

## 산출물 폴더

### crawling
- thread 성공: `etl/it_news/crawling/raw/thread/YYYY/MM/DD/success/*.csv`
- thread 실패: `etl/it_news/crawling/raw/thread/YYYY/MM/DD/fail/*.csv`
- comment 성공: `etl/it_news/crawling/raw/comment/YYYY/MM/DD/success/*.csv`
- comment 실패: `etl/it_news/crawling/raw/comment/YYYY/MM/DD/fail/*.csv`

### cleaning
- thread 성공: `etl/it_news/cleaning/cleaning/thread/YYYY/MM/DD/success/*.csv`
- thread 실패: `etl/it_news/cleaning/cleaning/thread/YYYY/MM/DD/fail/*.csv`
- comment 성공: `etl/it_news/cleaning/cleaning/comment/YYYY/MM/DD/success/*.csv`
- comment 실패: `etl/it_news/cleaning/cleaning/comment/YYYY/MM/DD/fail/*.csv`

### save
- thread 성공: `etl/it_news/save/save/thread/YYYY/MM/DD/success/*.csv`
- thread 실패: `etl/it_news/save/save/thread/YYYY/MM/DD/fail/*.csv`
- comment 성공: `etl/it_news/save/save/comment/YYYY/MM/DD/success/*.csv`
- comment 실패: `etl/it_news/save/save/comment/YYYY/MM/DD/fail/*.csv`

## 단계별 책임

### crawling
- `crawling/thread` 아래 스크립트로 사이트별 목록/본문 수집을 실행한다.
- 필수값 누락 또는 `state != ok` 행은 fail CSV로 분리한다.
- `run_comment_crawling.py`는 `crawling` 테이블에 저장된 글을 기준으로 댓글을 수집한다.

### cleaning
- `run_cleaning.py`는 thread raw 성공 파일만 읽어 `crawling` 테이블 형식으로 표준화한다.
- DB `MAX(created_at)` 조회가 가능하면 해당 시각 이후 데이터만 남긴다.
- DB 조회가 불가능하면 실행일 기준 3개월 전을 fallback 기준으로 사용한다.
- `run_comment_cleaning.py`는 댓글 CSV를 `comments` 적재용 형식으로 검증하고 중복 행을 제거한다.

### save
- `run_save.py`는 thread cleaning 성공 파일만 읽어 PostgreSQL `crawling` 테이블에 insert 한다.
- `run_comment_save.py`는 comment cleaning 성공 파일을 `comments` 테이블에 insert 한다.
- DB 연결 정보는 `PGHOST`, `PGPORT`, `PGDATABASE`, `PGUSER`, `PGPASSWORD` 또는 기본값을 사용한다.
- comment save는 `--comment-user-id` 또는 `IT_NEWS_COMMENT_USER_ID` 환경 변수가 필요하다.

## 제외 범위

- 이미지(`images`) 수집/저장은 이번 파이프라인에 포함하지 않는다.

## 의존성

- `etl/it_news/crawling/requirements.txt`
- `etl/it_news/cleaning/requirements.txt`
- `etl/it_news/save/requirements.txt`

## 참고 문서

- [local-database-setup.md](local-database-setup.md)
- [docs/PLAN.md](docs/PLAN.md)
- [docs/RESTRUCTURE_WORK_PLAN.md](docs/RESTRUCTURE_WORK_PLAN.md)
- [docs/RESTRUCTURE_WORK_RESULT.md](docs/RESTRUCTURE_WORK_RESULT.md)
