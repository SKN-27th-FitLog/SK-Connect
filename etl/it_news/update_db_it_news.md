# update_db_it_news — 실행 가이드

`update_db_it_news.py`는 IT 뉴스 ETL 단계를 **한 번에 순차 실행**하는 진입점이다. 크롤링·CSV·DB 오류 처리는 **각 단계 스크립트**에 맡기고, 이 파일은 **스크립트 존재 여부**와 **실행 순서**만 보장한다.

## 실행 방법

레포지토리 루트(`SK-Connect` 등 프로젝트 최상위)에서:

```bash
python etl/it_news/update_db_it_news.py
```

모든 하위 단계는 **현재 작업 디렉터리가 레포 루트**인 것과 동일하게 동작하도록 `subprocess`의 `cwd`를 레포 루트로 맞춘다. (특히 `02_cleaning_tables/cleaning_tables.py`가 출력 경로를 `etl\it_news\02_cleaning_tables\` 형태로 두므로 이 전제가 필요하다.)

## 실행 순서

1. `01_getter_threads/gatter_thread_pytorch.py`
2. `01_getter_threads/gatter_thread_geeknews.py`
3. `01_getter_threads/gatter_content_geeknews.py`
4. `01_getter_threads/gatter_content_pytorch.py`
5. `02_cleaning_tables/cleaning_tables.py`
6. `03_insert_tables/insert_tables.py`

동일 단계 안에서는 **병렬 실행 없음**. 소스(사이트)가 늘어나도 한 러너에서 부하·로그·CI 타임아웃을 예측하기 쉽도록 **항상 순차**로 둔다.

## 전제 조건

- **DB 삽입(6단계)** 은 PostgreSQL 연결과 환경 변수가 필요하다. 상세는 다음을 참고한다.
  - [local-database-setup.md](local-database-setup.md)
  - [03_insert_tables/insert_tables_runbook.md](03_insert_tables/insert_tables_runbook.md)
- Python 패키지(`pandas`, `psycopg` 등)는 각 스크립트 요구에 맞게 설치되어 있어야 한다. 이 오케스트레이터는 **의존성 검사를 하지 않는다.**

## 오케스트레이터 책임 범위

| 담당 | 담당하지 않음 |
|------|----------------|
| 위 6개 `.py` 경로 존재 여부 사전 검사 | 패키지·인터프리터 버전 검사 |
| 고정 순서로 `subprocess` 실행, 실패 시 즉시 중단 | 크롤 실패·CSV 누락·DB 오류의 세부 복구 (각 스크립트·런북) |

## `insert_tables` CSV 지정

`cleaning_tables.py`는 실행일 기준으로 `gatter_tables_YYMMDD.csv` 이름으로 저장한다. `insert_tables.py`는 **`--csv`를 생략하면** `02_cleaning_tables/gatter_tables_*.csv` 에 해당하는 파일을 **전부**(이름순) 읽어 합친 뒤, DB의 `MAX(created_at)` 보다 이후 행만 삽입한다. 특정 파일만 넣으려면 `--csv` 로 경로를 하나 이상 지정하면 된다.

## 소스(사이트) 추가 시

- **목록 수집(thread)** 스크립트와 **본문 수집(content)** 스크립트를 같은 패턴으로 추가한다.
- `update_db_it_news.py`의 `_STEPS` 튜플에 경로를 **thread 그룹 → content 그룹** 순으로 끼워 넣는다. (클린징·삽입 앞 순서는 유지.)

## 종료 코드

- `0`: 모든 단계 성공  
- `0`이 아님: 사전 검사 실패 또는 중간 단계에서 비정상 종료 (`subprocess` 예외)
