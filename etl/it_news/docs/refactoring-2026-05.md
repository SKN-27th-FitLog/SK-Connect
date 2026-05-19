# it_news 모듈화 리팩토링 (2026-05)

## 요약

- `common/postgresql/` → 루트 `postgresql/` 패키지로 분리
- DB 상수·SQL·DSN → `postgresql/config.py`
- 워터마크 `get_last_success_date` → `postgresql/watermark.py`
- 에러 문구 중앙화 → `common/errors.py` (`EtlErrors`)
- 크롤 공통 루프 → `common/crawling_http.py`
- 루트 `requirements.txt` 단일화

## 변경 전/후 디렉터리

### Before

```
it_news/
├── pipeline.py
├── common/
│   ├── constant.py, utils.py, preprocess.py, singleton.py
│   └── postgresql/
│       ├── connection.py
│       └── run_query.py
├── crawling/, cleaning/, save/
```

### After

```
it_news/
├── pipeline.py
├── postgresql/
│   ├── __init__.py, __main__.py
│   ├── config.py, singleton.py, connection.py
│   ├── run_query.py, watermark.py
├── common/
│   ├── constant.py, errors.py, utils.py, preprocess.py
│   └── crawling_http.py
├── crawling/, cleaning/, save/
```

## import 경로 변경표

| 이전 | 이후 |
|------|------|
| `from common.postgresql.connection import PostgreDB` | `from postgresql.connection import PostgreDB` |
| `from common.postgresql.run_query import ...` | `from postgresql.run_query import ...` |
| `from common.utils import get_last_success_date` | `from postgresql.watermark import get_last_success_date` |
| `from common.singleton import Singleton` | `from postgresql.singleton import Singleton` (패키지 내부만) |

## EtlErrors 코드 목록

| 코드 | 메서드 | 용도 |
|------|--------|------|
| `EtlErrors.Crawl` | `created_at_not_found()` | geeknews 작성일 파싱 실패 |
| `EtlErrors.Watermark` | `unsupported_service(service)` | 워터마크 조회 시 잘못된 Service |
| `EtlErrors.Preprocess` | `missing_columns_on_load()` | CSV에 created_at/thread 없음 |
| | `raw_root_missing(path)` | process=raw 루트 없음 |
| | `no_crawling_csv(service)` | 크롤 성공 CSV 없음 |
| | `cleaning_root_missing(path)` | process=cleaning 루트 없음 |
| | `no_cleaning_csv()` | 클리닝 성공 CSV 없음 |
| `EtlErrors.Save` | `merge_insert_failed()` | DB MERGE·INSERT 실패 |
| `EtlErrors.Db` | `connection_failed(detail)` | DB 연결 실패 |

## 실행 방법

`etl/it_news` 루트에서:

```bash
python pipeline.py
python -m crawling.crawling_thread_geeknews
python -m crawling.crawling_thread_pytorch
python cleaning/cleaning.py
python save/save.py
python -m postgresql
```

## 검증 체크리스트

- [ ] `python -c "from pipeline import run_pipeline; from postgresql.watermark import get_last_success_date"`
- [ ] `rg common.postgresql` → 0건 (문서 제외)
- [ ] `build_csv_path` 시그니처·CSV 경로 규칙 동일
- [ ] DB·네트워크 가능 시 `python pipeline.py` 또는 단계별 `__main__` 실행

## 의도적 미변경

- save 단계: DB thread 사전 필터 + MERGE ON thread (기능 중복 가능성, 별도 검토)
- `run_query._to_json_value_temp`: INSERT 직전 JSON 정규화 유지

## 관련 문서

- 코딩 기준: [etl-coding-standards.md](./etl-coding-standards.md)
- 기존: [it_news.md](./it_news.md), [local-database-setup.md](./local-database-setup.md) — import 예시는 추후 갱신 가능
