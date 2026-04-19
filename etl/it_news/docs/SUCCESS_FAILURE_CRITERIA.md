# IT News ETL 성공/실패 기준

이 문서는 현재 `etl/it_news` 코드 기준으로 `crawling`, `cleaning`, `save` 단계에서
무엇을 성공으로 보고 무엇을 실패로 분류하는지 정리한 기준 문서입니다.

대상 범위:
- `thread` 파이프라인
- `comment` 파이프라인

기준은 **현재 구현 코드의 실제 동작**을 설명하며, 이후 이 문서를 기준으로 판단 로직을 조정할 수 있습니다.

---

## 1. 공통 구조

### 산출물 저장 위치
- `crawling`
  - `thread`: `etl/it_news/crawling/raw/thread/YYYY/MM/DD/success|fail`
  - `comment`: `etl/it_news/crawling/raw/comment/YYYY/MM/DD/success|fail`
- `cleaning`
  - `thread`: `etl/it_news/cleaning/cleaning/thread/YYYY/MM/DD/success|fail`
  - `comment`: `etl/it_news/cleaning/cleaning/comment/YYYY/MM/DD/success|fail`
- `save`
  - `thread`: `etl/it_news/save/save/thread/YYYY/MM/DD/success|fail`
  - `comment`: `etl/it_news/save/save/comment/YYYY/MM/DD/success|fail`

### 성공/실패 판단 레벨
- **실행 단위 성공/실패**: 러너(`run_*.py`) 자체가 정상 종료했는지 여부
- **파일 단위 성공/실패**: 입력 CSV 1개를 성공 파일 또는 실패 파일로 보낼지 여부
- **행 단위 성공/실패**: 한 CSV 안의 각 row를 성공/실패로 분리할지 여부

---

## 2. Crawling 기준

## 2-1. `thread` crawling

대상 파일:
- `etl/it_news/crawling/run_crawling.py`
- `etl/it_news/crawling/common/runtime.py`

### 실행 단위 성공 기준
- 사이트별 수집 스크립트(`gatter_thread_*`, `gatter_content_*`)가 예외 없이 실행된다.
- 사이트별 처리 후 성공 row가 1건 이상 있으면 해당 소스는 성공으로 간주한다.
- 전체 실행 기준으로는 **어느 한 소스라도 성공 파일이 있어야** 정상 종료한다.

### 실행 단위 실패 기준
- 소스 처리 중 예외가 나면 해당 소스는 fail CSV로 기록된다.
- 전체 실행에서 성공 파일이 하나도 없으면 아래 메시지로 종료한다.
  - `수집 성공 파일이 없습니다.`

### 행 단위 성공 기준
`split_rows()` 기준으로 아래를 모두 만족하면 success row가 된다.
- `state == "ok"`
- `title` 존재
- `content` 존재
- 소스별 고유 ID 존재
  - GeekNews: `topic_id`
  - PyTorch: `topic_id`
- URL 존재
  - GeekNews: `article_url`
  - PyTorch: `topic_url`

### 행 단위 실패 기준
아래 중 하나라도 만족하지 못하면 fail row가 되며 `failure_reason`이 기록된다.
- `state_not_ok`
- `missing_topic_id`
- `missing_title`
- `missing_content`
- `missing_article_url`
- `missing_topic_url`

### 비고
- `required_fields` 인자가 전달되지만, 현재 실제 판정은 `state`, `id`, `title`, `content`, `url` 중심으로 고정되어 있다.
- success row가 없고 fail row만 있어도 fail CSV는 저장된다.

---

## 2-2. `comment` crawling

대상 파일:
- `etl/it_news/crawling/run_comment_crawling.py`
- `etl/it_news/crawling/comment/gatter_reply_geeknews.py`
- `etl/it_news/crawling/comment/gatter_reply_pytorch.py`

### 실행 단위 성공 기준
- 사이트별 댓글 수집 스크립트가 예외 없이 종료되면 그 소스는 성공으로 간주한다.
- `run_comment_crawling.py`는 **행 수가 0건이어도 스크립트가 정상 종료하면 success**로 본다.
- 전체 실행 기준으로는 어느 한 소스라도 정상 종료해야 정상 종료한다.

### 실행 단위 실패 기준
- 사이트별 수집 스크립트 실행 중 예외가 발생하면 fail CSV에 `source_name`, `failure_reason`만 기록한다.
- 전체 실행에서 성공한 소스가 하나도 없으면 아래 메시지로 종료한다.
  - `댓글 수집 성공 파일이 없습니다.`

### 행 단위 성공 기준
댓글 수집 스크립트 내부 기준:
- 대상 게시글 fetch/parse가 성공한다.
- 댓글 본문이 비어 있지 않다.
- 생성 시각을 파싱할 수 있거나, 파싱 실패 시 fallback 현재 시각으로 보완된다.

### 행 단위 실패 기준
- 개별 게시글 fetch 실패
- JSON 파싱 실패
- HTML/본문 추출 실패
- 빈 댓글 본문

### 비고
- 개별 게시글 실패는 stderr로만 남고, 해당 게시글 댓글은 결과 CSV에서 빠진다.
- 사이트 스크립트 자체가 끝까지 돌면 success CSV는 생성될 수 있다.
- 현재 comment crawling 단계는 **행 단위 failure CSV를 따로 만들지 않고**, 소스 실행 실패만 fail CSV로 기록한다.

---

## 3. Cleaning 기준

## 3-1. `thread` cleaning

대상 파일:
- `etl/it_news/cleaning/run_cleaning.py`
- `etl/it_news/cleaning/common/runtime.py`

### 실행 단위 성공 기준
- `crawling/raw/thread/.../success`에 대상 파일이 존재한다.
- 각 raw success 파일을 읽어 success row 또는 fail row로 분리 저장한다.
- 러너 자체는 파일이 하나라도 있으면 종료 코드 0으로 끝난다.

### 실행 단위 실패 기준
- 입력 파일이 없으면 아래 메시지로 종료한다.
  - `cleaning 대상 raw 성공 파일이 없습니다.`

### 행 단위 성공 기준
정규화 후 아래를 모두 만족해야 success row가 된다.
- `state == "ok"`
- `topic_id` 존재
- `title` 존재
- `content` 존재
- URL 존재
  - GeekNews: `article_url`
  - PyTorch: `topic_url` → 정규화 후 `article_url`로 매핑
- 생성 시각 존재
  - GeekNews: `posted_at`
  - PyTorch: `created_at`
- 같은 배치 내에서 `article_url`이 중복되지 않음
- `created_at > cutoff`

### 행 단위 실패 기준
아래 조건에 해당하면 fail row가 된다.
- `state_not_ok`
- `missing_topic_id`
- `missing_title`
- `missing_content`
- `missing_article_url`
- `missing_topic_url`
- `missing_created_at`
- `duplicate_article_url`
- `older_than_cutoff`
- `unknown_source`
- `normalize_failed`

### cutoff 기준
- 우선 DB의 `MAX(created_at)` 조회값 사용
- DB 조회 실패 시 실행일 기준 3개월 전 fallback 사용

### 비고
- success row가 하나도 없어도 fail row가 있으면 fail CSV는 저장된다.
- success row와 fail row가 동시에 있을 수 있다.
- `view_count`, `comment_count`, `point`, `author`, `category_cd`는 정규화 과정에서 기본값/변환값이 채워진다.

---

## 3-2. `comment` cleaning

대상 파일:
- `etl/it_news/cleaning/run_comment_cleaning.py`

### 실행 단위 성공 기준
- `crawling/raw/comment/.../success`에 대상 파일이 존재한다.
- 각 comment raw success 파일을 읽어 success row 또는 fail row로 분리 저장한다.

### 실행 단위 실패 기준
- 입력 파일이 없으면 아래 메시지로 종료한다.
  - `cleaning 대상 comment raw 성공 파일이 없습니다.`

### 행 단위 성공 기준
정규화 후 아래를 모두 만족해야 success row가 된다.
- `thread` 존재
- `crawling_id` 존재
- `crawling_id`가 정수로 변환 가능
- `content` 존재
- `created_at` 존재 및 `datetime.fromisoformat()` 가능
- `modify_at` 존재 및 `datetime.fromisoformat()` 가능
- 같은 실행 배치 내에서 `(crawling_id, created_at, content)` 조합이 중복되지 않음

### 행 단위 실패 기준
- `missing_thread`
- `missing_crawling_id`
- `invalid_crawling_id`
- `missing_content`
- `missing_created_at`
- `invalid_created_at`
- `missing_modify_at`
- `invalid_modify_at`
- `duplicate_comment`

### 비고
- `post_id`는 현재 비워둔 상태로 success 파일에 들어간다.
- `status_cd`는 기본값 `ST01` 또는 CLI 인자 `--status-cd` 값으로 채운다.

---

## 4. Save 기준

## 4-1. `thread` save

대상 파일:
- `etl/it_news/save/run_save.py`
- `etl/it_news/save/common/runtime.py`

### 실행 단위 성공 기준
- `cleaning/cleaning/thread/.../success`에 대상 파일이 존재한다.
- DB 연결에 성공한다.
- 각 파일에 대해 INSERT 예외 없이 끝나면 success CSV를 저장한다.

### 실행 단위 실패 기준
- 입력 파일이 없으면 아래 메시지로 종료한다.
  - `save 대상 cleaning 성공 파일이 없습니다.`
- DB 연결 실패 시 아래 형식으로 출력 후 종료 코드 `1` 반환
  - `DB 연결 실패: ...`

### 파일 단위 성공 기준
- `filter_incremental()` 적용 후 남은 DataFrame을 `insert_dataframe()`으로 적재
- INSERT 예외가 발생하지 않음
- 적재 row 수가 `0`이어도 예외가 없으면 success 처리

### 파일 단위 실패 기준
- `insert_dataframe()` 또는 commit 과정에서 예외 발생
- 실패 시:
  - 원본 DataFrame을 fail CSV로 저장
  - 예외 문자열을 `.log` 파일로 저장
  - 콘솔에 `[fail] ...` 출력

### 추가 필터 기준
`filter_incremental()` 기준:
- `created_at` 파싱 불가 row는 적재 대상에서 제외
- DB의 `MAX(created_at)`보다 이후 데이터만 남김
- DB에 데이터가 없으면 파싱 가능한 row는 모두 남김

### 비고
- 적재 직전 문자열 길이 제한, 빈 문자열 → `None` 변환, `map_id` 정수 변환 등이 적용된다.
- 현재는 적재 대상에서 빠진 row를 별도 fail CSV로 보내지 않고, success 결과에는 필터 후 DataFrame만 기록한다.

---

## 4-2. `comment` save

대상 파일:
- `etl/it_news/save/run_comment_save.py`
- `etl/it_news/save/common/runtime.py`

### 실행 단위 성공 기준
- `cleaning/cleaning/comment/.../success`에 대상 파일이 존재한다.
- `user_id`를 확보한다.
  - `--user-id` 인자 또는 `IT_NEWS_COMMENT_USER_ID` / `COMMENT_USER_ID`
- DB 연결에 성공한다.
- 각 파일에 대해 INSERT 예외 없이 끝나면 success CSV를 저장한다.

### 실행 단위 실패 기준
- 입력 파일이 없으면 아래 메시지로 종료한다.
  - `save 대상 comment cleaning 성공 파일이 없습니다.`
- `user_id`를 찾지 못하면 아래 메시지로 종료한다.
  - `comment save용 user_id가 없습니다. --user-id 또는 IT_NEWS_COMMENT_USER_ID를 설정하세요.`
- DB 연결 실패 시 아래 형식으로 출력 후 종료 코드 `1` 반환
  - `DB 연결 실패: ...`

### 파일 단위 성공 기준
- DB에 이미 있는 댓글과 동일한 `(crawling_id, created_at, content)` 조합을 제외한 후
- 남은 DataFrame을 `insert_comment_dataframe()`으로 적재
- INSERT 예외가 발생하지 않음
- 적재 row 수가 `0`이어도 예외가 없으면 success 처리

### 파일 단위 실패 기준
- `existing_comment_keys()` 조회, `insert_comment_dataframe()`, commit 중 예외 발생
- 실패 시:
  - 원본 DataFrame을 fail CSV로 저장
  - 예외 문자열을 `.log` 파일로 저장
  - 콘솔에 `[fail] ...` 출력

### 비고
- `post_id`는 현재 비어 있어도 적재 가능하도록 처리된다.
- `status_cd`는 row 값 또는 기본값 `ST01`을 사용한다.
- DB 중복 제거는 save 단계에서 한 번 더 수행된다.

---

## 5. 현재 기준에서 특히 조정 검토가 필요한 지점

현재 문서를 기준으로 이후 판단 로직을 조정할 때 우선 검토할 만한 포인트:

1. `thread crawling`의 성공/실패 기준이 `required_fields` 인자와 완전히 연동되어 있지 않음
2. `comment crawling`은 행 단위 fail CSV가 없고, 게시글별 실패를 stderr에만 남김
3. `thread save`는 `filter_incremental()`로 제외된 row를 실패로 기록하지 않음
4. `comment save`는 적재 row 수가 0건이어도 success로 간주함
5. `cleaning`의 duplicate 기준이 `thread`는 `article_url`, `comment`는 `(crawling_id, created_at, content)`로 서로 다름

---

## 6. 관련 코드

- `etl/it_news/crawling/run_crawling.py`
- `etl/it_news/crawling/run_comment_crawling.py`
- `etl/it_news/crawling/common/runtime.py`
- `etl/it_news/cleaning/run_cleaning.py`
- `etl/it_news/cleaning/run_comment_cleaning.py`
- `etl/it_news/cleaning/common/runtime.py`
- `etl/it_news/save/run_save.py`
- `etl/it_news/save/run_comment_save.py`
- `etl/it_news/save/common/runtime.py`
