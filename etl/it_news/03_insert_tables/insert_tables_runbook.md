# `insert_tables.py` 실행 계획·동작 요약 (사후검증용)

## 목적

정제된 IT 뉴스 CSV를 PostgreSQL **`"crawling"`** 테이블에 **증분**으로 넣습니다. DB에 이미 적재된 `created_at` 최댓값보다 **이후**인 행만 삽입하고, `crawling_id`는 DB 시퀀스(`BIGSERIAL`)가 자동 부여합니다.

## 선행 조건

- PostgreSQL이 접근 가능할 것 (로컬 예: [database/docker-compose.yml](../../database/docker-compose.yml)로 `sk_connect_db` 기동).
- 기본 연결 정보(환경 변수 미설정 시):
  - `PGHOST` = `localhost`
  - `PGPORT` = `5432`
  - `PGDATABASE` = `service`
  - `PGUSER` = `user`
  - `PGPASSWORD` = `password123`
- Python 패키지: [etl/it_news/requirements.txt](../requirements.txt) 설치 (`pandas`, `psycopg[binary]` 등).

```powershell
cd C:\dev\project\SK-Connect\etl\it_news
pip install -r requirements.txt
```

## 실행 방법

```powershell
cd C:\dev\project\SK-Connect\etl\it_news\03_insert_tables
python insert_tables.py --csv "..\02_cleaning_tables\gatter_tables_260408.csv"
```

- `--csv` 를 생략하면 기본값으로 `..\02_cleaning_tables\gatter_tables_260408.csv` 를 사용합니다. 날짜별로 바뀌는 파일은 **항상 `--csv`로 경로를 지정**하면 됩니다.
- 연결은 `PG*` 환경 변수로 덮어쓸 수 있습니다.

## 처리 파이프라인 (실행 순서)

1. **연결 1회 검증**: `psycopg.connect` 후 `SELECT 1` 로 성공 여부 확인. 실패 시 메시지 출력 후 종료 코드 `1`.
2. **`MAX(created_at)` 조회**: 아래 SQL로 `crawling` 테이블의 마지막 수집 시각 기준을 가져옵니다. 테이블이 비어 있으면 `NULL`.
3. **CSV 로드**: `pandas.read_csv` 로 읽고, `created_at` 을 UTC 기준으로 파싱합니다. 파싱 불가 행은 제외하고 건수를 stderr에 경고할 수 있습니다.
4. **증분 필터**: `MAX(created_at)` 이 `NULL`이 아니면, 파싱된 `created_at`(UTC)이 DB에서 읽은 최댓값(UTC로 정규화)보다 **큰** 행만 남깁니다 (`>`). 동일 시각 재삽입을 줄이기 위함입니다.
5. **INSERT**: `crawling_id` 컬럼 없이 아래 컬럼만 삽입합니다. `cursor.executemany` 로 일괄 실행 후 `commit`.

### 사용 SQL (요약)

**최댓값 조회**

```sql
SELECT MAX("created_at") FROM "crawling";
```

**삽입 (컬럼·플레이스홀더)**

```sql
INSERT INTO "crawling" (
    title, content, thread, article_url, created_at,
    view_count, comment_count, point, author, map_id, category_cd
) VALUES (
    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
);
```

- 스키마 정의: [database/init.sql](../../database/init.sql) 의 `"crawling"` 테이블.

## 스크립트 내 데이터 가공

- **문자열 길이**: `title`(200), `thread`(20), `article_url`(500), `author`(100), `category_cd`(6) 초과 시 잘라서 DB 제약 위반을 방지합니다.
- **빈 문자열 / 결측**: `map_id`, `category_cd` 등은 빈 문자열을 `NULL` 로 넣어 FK·타입 오류를 줄입니다.
- **`created_at`**: CSV ISO 문자열(타임존 포함 가능)을 파싱해 DB에 전달합니다.

## 기대 동작·엣지 케이스

| 상황 | 기대 결과 |
|------|-----------|
| `crawling` 이 비어 있음 | `MAX(created_at)` 이 `NULL` → CSV에 파싱 가능한 모든 행 삽입 시도 |
| 동일 CSV로 재실행 | 이미 DB의 최댓값 이하/동일 시각은 필터에서 제외 → **0건** 삽입 가능 |
| 연결 실패 | stderr에 오류, 종료 코드 `1` |
| `created_at` 파싱 실패 행 | 해당 행 제외(경고 출력) |

## 사후검증 체크리스트

DB에 접속한 뒤 예시:

```sql
SELECT COUNT(*) FROM "crawling";
SELECT MAX("created_at") FROM "crawling";
SELECT crawling_id, title, article_url, created_at
FROM "crawling"
ORDER BY crawling_id DESC
LIMIT 5;
```

- 첫 적재 후: CSV 행 수(파싱 제외분 반영)와 `COUNT(*)` 증가가 일치하는지 확인.
- 재실행 후: `COUNT(*)` 변화 없음, `INSERT 완료: 0건` 출력 확인.

## 로컬 검증 이력 (참고)

- 동일 CSV 최초 적재 후 `INSERT` 성공, 동일 CSV 재실행 시 필터 결과 0건·`INSERT 완료: 0건` 확인.
