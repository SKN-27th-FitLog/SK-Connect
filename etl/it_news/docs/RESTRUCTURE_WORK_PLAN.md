# IT News ETL 재구성 사전 계획

## 기준
- 최우선 문서: `etl/it_news/docs/PLAN.md`
- 작업 범위: `etl/it_news` 내부만 재구성
- 참고 구현: `01_getter_threads`, `02_cleaning_tables`, `03_insert_tables`, `04_update_threads`, `update_db_it_news.py`

## 목표
- `thread`와 `comment`를 같은 `crawling -> cleaning -> save` 규칙으로 재정리한다.
- 모든 산출물 경로를 `.../<kind>/YYYY/MM/DD/success|fail` 구조로 통일한다.
- 새 코드가 레거시 폴더를 직접 참조하지 않게 만들어 최종 삭제 가능 상태로 만든다.
- `comments` 적재까지 포함하되, `images` 관련 로직은 이번 범위에서 제외한다.

## 구현 방침
1. `thread` 수집 스크립트는 `crawling/thread`로 옮기고, `run_crawling.py`가 새 위치를 직접 호출한다.
2. 댓글 수집 스크립트는 `crawling/comment`로 옮기고, `run_comment_crawling.py`를 별도 러너로 둔다.
3. 수집/정제/저장 경로는 모두 `thread` / `comment` 하위 버킷을 가진다.
4. `run_comment_cleaning.py`와 `run_comment_save.py`를 추가해 `comments` 테이블 적재까지 이어진다.
5. 과도한 공통화 대신 각 단계 러너를 분리해 읽기 쉬운 구조를 유지한다.
6. 실행 전후 기록은 `docs` 아래 문서로 남긴다.

## 제외 항목
- `images` 테이블 insert
- 이미지 수집 스크립트의 새 구조 이관
