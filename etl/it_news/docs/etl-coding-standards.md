# SK-Connect ETL 코딩 기준 (it_news)

이 문서는 it_news ETL 및 동일 패턴 작업 시 적용하는 **프로젝트별** 코드 구조·수정 규칙의 원본이다. 범용 함수·레이어 배치 양식은 Cursor Skill **`code-structure-standards`** (`~/.cursor/skills/code-structure-standards/SKILL.md`)를 따른다.

## 1. 디렉터리·진입점

| 규칙 | 내용 |
|------|------|
| 루트 오케스트레이션 | `it_news/` 루트에 실행·파이프라인 제어용 `.py`는 **`pipeline.py` 하나만** 둔다. |
| 단계 모듈 `__main__` | `crawling/`, `cleaning/`, `save/`는 개발·디버그용 단독 실행(`if __name__ == "__main__"`)을 **허용**한다. |
| DB 테스트 | `postgresql/connection.py`에 `__main__`을 두지 않는다. `python -m postgresql`로 연결·샘플 쿼리를 검증한다. |

## 2. `common/` vs `postgresql/` 책임

| 패키지 | 역할 |
|--------|------|
| `common/` | ETL·크롤·CSV·전처리·에러 메시지 등 **DB 연결 없이** 재사용 가능한 로직 |
| `postgresql/` | 연결, 쿼리, 워터마크, **DB 전용 상수** (`config.py`) |

- DB 환경변수 키·테이블명·워터마크 SQL은 **`postgresql/config.py`에만** 정의한다.
- `common/utils.py`는 CSV·경로·시간 유틸만 담당하며 **PostgreSQL을 import하지 않는다.**
- 워터마크 조회는 `postgresql/watermark.py`의 `get_last_success_date()`를 사용한다.

## 3. 에러 메시지

- 사용자·로그·`raise`용 문구는 **`common/errors.py`의 `EtlErrors`**에만 정의한다.
- 코드 = 중첩 클래스·메서드명 (예: `EtlErrors.Crawl.created_at_not_found()`).
- 크롤 fail CSV의 `error` 컬럼에 넣는 `str(e)`(파싱 예외 원문)는 예외적으로 인라인 허용.

## 4. 상수·네이밍

- 단계·상태·컬럼·코드 테이블: `common/constant.py`의 Enum·클래스 유지.
- 클리닝·save CSV prefix: `ItNewsFilePrefix.DEFAULT` 사용 (문자열 `"it_news"` 하드코딩 금지).
- 기존 함수·Enum 이름을 불필요하게 바꾸지 않는다.

## 5. 공통화·최소 diff

- 재사용성이 높은 로직만 `common/` 하위 모듈로 추출한다 (예: `crawling_http.py`).
- 사이트별 파싱·selector는 `crawling/` 소스 파일에 둔다.
- 동작 변경 없는 리팩터링을 우선한다. 의심되는 중복(예: save 사전 thread 필터 + MERGE)은 별도 이슈로 분리한다.

## 6. 의존성

- 루트 [`requirements.txt`](../requirements.txt)를 단일 소스로 한다.
- `crawling/`, `cleaning/`, `save/requirements.txt`는 `-r ../requirements.txt`만 참조한다.

## 7. 실행

작업 디렉터리는 **`etl/it_news` 루트**이다.

```bash
# 전체 파이프라인
python pipeline.py

# 단계별 (개발용)
python -m crawling.crawling_thread_geeknews
python -m crawling.crawling_thread_pytorch
python cleaning/cleaning.py
python save/save.py

# DB 연결 테스트
python -m postgresql
```

## 8. 문서

- 설계·flow·단계 동작: [design.md](./design.md)
- 본 기준 문서 수정 시 Skill 배포본(`code-structure-standards`)도 필요 시 동기화한다.
