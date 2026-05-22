# 코드 무결성 및 테스트 기준 — it_news

> 범용 원본: Cursor Skill **`code-integrity-and-testing`**.  
> 본 문서는 **etl/it_news** 적용·체크리스트용이다.

작업 전·후 [design.md](./design.md), [function-inventory.md](./function-inventory.md), [testing.md](./testing.md)를 함께 본다.

---

## 목적

| 목표 | 설명 |
|------|------|
| 동작 기준 | docstring `Note:` · 인벤토리와 구현 일치 |
| 테스트 통일 | 시나리오 ID `IT-L*` · [testing.md](./testing.md) 단일 기준 |
| 회귀 방지 | Level 0 불변 규칙·MERGE 키(`thread`) 우선 |
| 안전한 테스트 | pytest 중 **`crawling` MERGE 금지** (G1) |

**쓰기 유일 경로(운영):** `postgresql.run_query.insert_crawling_batch` (`autocommit`, rollback 없음).

---

## 필수 순서

```
함수 계약(docstring Note:) → 테스트 케이스(testing.md) → tests/ 구현
```

테스트 코드 작성 **전에** [testing.md](./testing.md)에 시나리오가 있어야 한다.

**기존 테스트 수정:** Skill `code-integrity-and-testing` §9.1 · [testing.md §2.1](./testing.md) — 구현에 맞춰 assert만 고치지 않는다(불변·INV 유지, 신규는 새 `IT-L*` ID). 검토 없이 조정하면 방어선 침범·작업 2배화 위험.

---

## it_news 핵심 불변 규칙

| ID | 규칙 | 검증 대상 |
|----|------|-----------|
| INV-01 | CSV 경로 `process={raw\|cleaning\|save}/information_cd=…/year=…/month=…/day=…/status=…/{prefix}_{HHMMSS}.csv` | `build_csv_path` |
| INV-02 | raw 파일 prefix = `geeknews` / `pytorch`; cleaning·save 기본 = `it_news` | `Stage`, `ItNewsFilePrefix` |
| INV-03 | `thread` = `{service}_` + 사이트 고유 ID; DB MERGE 키 | slicing, `insert_crawling_batch` |
| INV-04 | 크롤 success만 `created_at > 워터마크` | `run_crawl_and_save` |
| INV-05 | 클리닝 `state=fail` — 필수 컬럼 결측·전처리 예외 | `cleaning_data_in_df` |
| INV-06 | save 전 DB 기존 `thread` 행 제외 | `save_threads` |
| INV-07 | IT 크롤 기본 코드 `information_cd=IC02`, `category_cd=CA07` | `CodeTable` |
| INV-08 | DB 비었을 때 워터마크 = 오늘−`ETL_CRAWL_LOOKBACK_DAYS`(90)일 00:00 | `default_last_collected_at` |

---

## 함수 유형·안전성 (요약)

[function-inventory.md](./function-inventory.md) 전체 표 참고.

| 레이어 | 권장 테스트 등급 |
|--------|------------------|
| `common/` (전처리·경로·시간) | Level 0 단위 |
| `postgresql/` READ | Level 1 mock |
| `postgresql/` MERGE, CSV 쓰기 | Level 2 mock·간접 |
| `crawling/` HTTP | Level 3 mock `requests` |
| `pipeline.py`, 단계 `*_threads` | Level 2~3 patch 간접 |

---

## 완료 조건 (유지보수)

- [x] 함수 인벤토리 · docstring `Note:`
- [x] 테스트 케이스 문서 (`testing.md`)
- [x] `tests/conftest.py` G1 가드
- [x] pytest 59건 (`tests/unit/`)
- [ ] 로컬 passed 확인 · CI job

---

## 관련 문서

- [testing.md](./testing.md) — 시나리오·가드레일·실행(구현 후)
- [function-inventory.md](./function-inventory.md)
- [etl-coding-standards.md](./etl-coding-standards.md)
