# IT News 설정 외부화 작업 보고서

## 개요
`etl/it_news` 내부의 DB 연결값과 운영용 고정값을 코드에서 분리해 각 스테이지 폴더의 설정 파일에서 읽도록 정리했다.

- DB 연결값: `crawling/.env`, `cleaning/.env`, `save/.env`
- 운영 설정값: `crawling/config.json`, `cleaning/config.json`, `save/config.json`
- 설정 로더: 각 스테이지의 `common/settings.py`

## 적용 내용
### 1. DB 연결값 `.env` 파일화
- `PGHOST`, `PGPORT`, `PGDATABASE`, `PGUSER`, `PGPASSWORD`를 각 스테이지 폴더의 `.env`에서 읽도록 변경했다.
- `save/run_comment_save.py`의 댓글 저장 사용자 ID 탐색도 `save/config.json`에 정의한 환경변수 키 순서를 따르도록 정리했다.

### 2. `crawling` 설정 외부화
- 엔트리포인트 기본값(`limit`, `timeout`, `content-timeout`, `content-delay`, `sleep-seconds`)을 `crawling/config.json`으로 이동했다.
- 소스별 URL, User-Agent, 최대 페이지 수, 출력 파일명, 댓글 수집 제한, PyTorch post chunk 크기 등을 `crawling/config.json`으로 이동했다.
- `.tmp` 경로명, 성공/실패 디렉터리명, CSV 인코딩, 출력 파일 시간 포맷도 설정에서 읽도록 변경했다.

### 3. `cleaning` 설정 외부화
- fallback 증분 기준 일수와 DB connect timeout을 `cleaning/config.json`으로 이동했다.
- GeekNews/PyTorch 정규화 시 사용하는 길이 제한, thread prefix, source name, 기본 `category_cd`를 설정으로 이동했다.
- comment cleaning의 기본 `status_cd`도 설정에서 읽도록 변경했다.

### 4. `save` 설정 외부화
- DB connect timeout, 길이 제한, comments 기본 상태 코드, 상태 코드 최대 길이, comment user ID 환경변수 키 목록을 `save/config.json`으로 이동했다.
- `save` 입력/출력 경로 버킷과 CSV 인코딩도 설정 기반으로 바꿨다.
- DB 테이블명은 `save/config.json`의 값을 바탕으로 SQL을 생성하도록 정리했다.

## 생성/수정된 핵심 파일
- `etl/it_news/crawling/common/settings.py`
- `etl/it_news/crawling/config.json`
- `etl/it_news/crawling/.env`
- `etl/it_news/cleaning/common/settings.py`
- `etl/it_news/cleaning/config.json`
- `etl/it_news/cleaning/.env`
- `etl/it_news/save/common/settings.py`
- `etl/it_news/save/config.json`
- `etl/it_news/save/.env`
- `etl/it_news/docs/local-database-setup.md`

## 검증 결과
### 정적 확인
- `ReadLints` 기준으로 `etl/it_news/crawling`, `etl/it_news/cleaning`, `etl/it_news/save`에서 새 lint 오류가 없음을 확인했다.

### 엔트리포인트 실행 확인
아래 스크립트들이 `--help` 기준으로 정상 실행되는 것을 확인했다.

- `etl/it_news/crawling/run_crawling.py`
- `etl/it_news/crawling/run_comment_crawling.py`
- `etl/it_news/cleaning/run_cleaning.py`
- `etl/it_news/cleaning/run_comment_cleaning.py`
- `etl/it_news/save/run_save.py`
- `etl/it_news/save/run_comment_save.py`
- `etl/it_news/crawling/thread/gatter_thread_geeknews.py`
- `etl/it_news/crawling/thread/gatter_thread_pytorch.py`
- `etl/it_news/crawling/thread/gatter_content_geeknews.py`
- `etl/it_news/crawling/thread/gatter_content_pytorch.py`
- `etl/it_news/crawling/comment/gatter_reply_geeknews.py`
- `etl/it_news/crawling/comment/gatter_reply_pytorch.py`

### `.env` 기반 DB 확인
- `save/common/runtime.py`의 `connect()`로 실제 DB 연결 및 `MAX(created_at)` 조회 성공
- `cleaning/common/runtime.py`의 `fetch_last_created_at()` 조회 성공
- `crawling/comment/gatter_reply_geeknews.py`의 DB 연결 파라미터가 `.env` 기준으로 정상 조립되는 것 확인

### 주석 및 가독성 정리
- 최근 변경한 `crawling`, `cleaning`, `save` 코드에 파트 설명 주석과 함수/설정 설명을 추가했다.
- 사용하지 않던 `config_value()` 헬퍼는 제거해 설정 로더를 단순화했다.
- 일부 스크립트는 CSV 인코딩 상수를 config 기반으로 통일해 하드코딩을 줄였다.

## 참고
- 현재 `.env` 파일에는 로컬 확인값이 들어가 있다.
- 이후 운영 환경 값이 바뀌면 코드 수정 없이 각 스테이지 폴더의 `.env` 또는 `config.json`만 갱신하면 된다.
