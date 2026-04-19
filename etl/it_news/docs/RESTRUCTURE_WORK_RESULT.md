# IT News ETL 재구성 작업 결과

## 적용 내용
- `etl/it_news/crawling`, `etl/it_news/cleaning`, `etl/it_news/save` 디렉터리를 추가했다.
- 각 단계에 `common` 폴더와 `requirements.txt`를 추가했다.
- 기존 `01_getter_threads` / `02_cleaning_tables` / `03_insert_tables` 로직을 새 단계 러너에서 재사용하도록 연결했다.
- `etl/it_news/update_db_it_news.py`를 새 3단계 파이프라인 진입점으로 변경했다.
- 실행 전/후 확인용 문서를 `etl/it_news/docs` 아래에 추가했다.

## 단계별 결과
### crawling
- `run_crawling.py`가 GeekNews, PyTorchKR 수집을 순차 실행한다.
- 성공 파일은 `crawling/raw/YYYY/MM/DD/success/*.csv`
- 실패 파일은 `crawling/raw/YYYY/MM/DD/fail/*.csv`

### cleaning
- `run_cleaning.py`가 raw 성공 파일을 읽어 `crawling` 테이블 형식으로 표준화한다.
- DB 최종 `created_at` 조회가 가능하면 그 시각 이후 데이터만 남기고, 실패 시 3개월 fallback을 사용한다.
- 성공/실패 파일을 `cleaning/cleaning/YYYY/MM/DD/...`에 분리 저장한다.

### save
- `run_save.py`가 cleaning 성공 파일만 읽어 `crawling` 테이블에 insert 한다.
- 저장 성공/실패 파일을 `save/save/YYYY/MM/DD/...`에 분리 저장한다.
- DB 연결 실패 시 메시지를 출력하고 종료한다.

## 검증 결과
- `python -m py_compile`로 새 스크립트 문법 검사를 완료했다.
- `python etl/it_news/crawling/run_crawling.py --limit 1` 실행 확인
- `python etl/it_news/cleaning/run_cleaning.py` 실행 확인
- `python etl/it_news/save/run_save.py`는 로컬 PostgreSQL 미기동 상태에서 연결 타임아웃으로 실패 확인

## 후속 확인 포인트
- `database/docker-compose.yml` 기준으로 PostgreSQL을 기동한 뒤 `save` 단계를 다시 검증해야 한다.
- `comments` / `images` 테이블 적재는 별도 정책 확정 후 다음 단계에서 확장해야 한다.
