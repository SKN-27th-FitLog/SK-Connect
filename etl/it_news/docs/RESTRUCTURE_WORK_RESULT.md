# IT News ETL 재구성 작업 결과

## 적용 내용
- `etl/it_news/crawling`, `etl/it_news/cleaning`, `etl/it_news/save` 디렉터리를 추가했다.
- 각 단계에 `common` 폴더와 `requirements.txt`를 추가했다.
- `thread` 스크립트를 `etl/it_news/crawling/thread`로 옮기고 `01_getter_threads` 의존을 제거했다.
- `04_update_threads`의 댓글 수집 로직을 `crawling/comment` / `run_comment_crawling.py`로 이관했다.
- `etl/it_news/update_db_it_news.py`를 `thread` / `comment` 대상 선택이 가능한 진입점으로 변경했다.
- 실행 전/후 확인용 문서를 `etl/it_news/docs` 아래에 추가했다.

## 단계별 결과
### crawling
- `run_crawling.py`가 `crawling/thread` 아래 스크립트로 GeekNews, PyTorchKR 본문 수집을 실행한다.
- `run_comment_crawling.py`가 `crawling` 테이블을 기준으로 댓글 수집을 실행한다.
- 성공 파일은 `crawling/raw/thread/YYYY/MM/DD/success/*.csv`, `crawling/raw/comment/YYYY/MM/DD/success/*.csv`
- 실패 파일은 `crawling/raw/thread/YYYY/MM/DD/fail/*.csv`, `crawling/raw/comment/YYYY/MM/DD/fail/*.csv`

### cleaning
- `run_cleaning.py`가 raw 성공 파일을 읽어 `crawling` 테이블 형식으로 표준화한다.
- `run_comment_cleaning.py`가 comment raw 성공 파일을 읽어 `comments` 적재 형식으로 표준화한다.
- DB 최종 `created_at` 조회가 가능하면 그 시각 이후 데이터만 남기고, 실패 시 3개월 fallback을 사용한다.
- 성공/실패 파일을 `cleaning/cleaning/thread/YYYY/MM/DD/...`, `cleaning/cleaning/comment/YYYY/MM/DD/...`에 분리 저장한다.

### save
- `run_save.py`가 cleaning 성공 파일만 읽어 `crawling` 테이블에 insert 한다.
- `run_comment_save.py`가 comment cleaning 성공 파일을 읽어 `comments` 테이블에 insert 한다.
- 저장 성공/실패 파일을 `save/save/thread/YYYY/MM/DD/...`, `save/save/comment/YYYY/MM/DD/...`에 분리 저장한다.
- DB 연결 실패 시 메시지를 출력하고 종료한다.

## 검증 결과
- `python -m py_compile`로 새 스크립트 문법 검사를 완료했다.
- `python etl/it_news/crawling/run_crawling.py --limit 1` 실행 확인
- `python etl/it_news/cleaning/run_cleaning.py` 실행 확인
- `python etl/it_news/save/run_save.py`는 로컬 PostgreSQL 미기동 상태에서 연결 타임아웃으로 실패 확인
- `comment` 파이프라인은 DB와 `comments.user_id` 기본값이 있어야 저장 검증 가능

## 후속 확인 포인트
- `database/docker-compose.yml` 기준으로 PostgreSQL을 기동한 뒤 `save` 단계를 다시 검증해야 한다.
- `IT_NEWS_COMMENT_USER_ID` 또는 `--comment-user-id`로 comment 저장용 사용자 ID를 확정해야 한다.
- 이미지(`images`) 수집/적재는 별도 정책 확정 후 다음 단계에서 확장해야 한다.
