# post_analysis 리팩토링 이력

code-structure-standards(구 sk-connect-etl-standards) 기준으로 2026-05 구조 정리.  
오케스트레이션은 루트 스크립트 3개 + 외부 스케줄러 연동.

## Phase 1 — 인프라 분리

- `common/postgresql/` → 루트 `postgresql/` 승격
- DB 상수·MERGE SQL → `postgresql/config.py`
- `connection.py` `__main__` 제거 → `python -m postgresql`
- 루트 스크립트 import: `postgresql.run_query`

## Phase 2 — 에러 중앙화

- `common/errors.py` — `PostAnalysisErrors` (Sentiment, LlmKeywords, GetReviews, Db)
- 배치 스크립트 컬럼 누락 `ValueError` 통합

## Phase 3 — BERT 통합

- `analyze_sentimental.py` → `BertTokenizer` 사용, 모듈 import 시 모델 로드 제거
- `BertTokenizer`에 `Singleton` 적용

## Phase 4 — MERGE·스키마

- MERGE SQL에 `information_cd` 추가
- `get_reviews`: 식당 리뷰 적재 시 `information_cd=IC01` (`CodeTable.INFORMATION_RESTAURANT`)
- `WHEN MATCHED` UPDATE 전 컬럼 `COALESCE(x.col, a.col)` — 부분 MERGE NULL 덮어쓰기 방지

## Phase 5 — 운영 정리

- `analyze_keywords_by_llm`: `max_rows` 인자 (테스트·batch 청크)
- `common/env.py` — `load_dotenv` 일원화
- `requirements.txt`: `python-dotenv`, `langchain-openai` pin
- `.gitignore`: `.venv`, `.env`, `__pycache__` 등

## Phase 6 — 파이프라인 단순화

- 제거: `analyze_keywords.py` (Kiwi), `classify_keywords.py` (긍·부정 키워드 분류)
- 제거: `kiwipiepy`, `KiwiPosTagPrefix`, `AnalyzeKeywordsConfig`, `ClassifyKeywordsConfig`, `KeywordFormat`
- `errors.py`: `KiwiKeywords`, `ClassifyKeywords` 삭제
- [design.md](design.md) — 3단계 파이프라인·다이어그램 정비

## Phase 7 — DB 스키마 동기화

- 실 DB 조회: `analysis`에 `positive_kw`/`negative_kw` **없음**, `shop_cd` **있음**
- `postgresql/config.py` MERGE SQL — 존재하지 않는 컬럼 제거, `title`(200)·`sentimental`(16) 길이 DB와 일치
- `common/constant.py` — `POSITIVE_KW`/`NEGATIVE_KW` 제거, `SHOP_CD`는 DB 전용(미 MERGE)으로 문서화
- [design.md](design.md) — 실측 스키마·`shop_cd` 미관리·제거 단계 문구 수정

## Phase 8 — pipeline.py

- `pipeline.py` — `run_pipeline()`: get_reviews → analyze_sentimental → analyze_keywords_by_llm
- `PostAnalysisErrors.Pipeline` — 단계 로그·실패·`max_rows` 검증 메시지
- CLI: `python pipeline.py [--max-rows N]`

## Phase 9 — shop_id / shop_cd 매칭

- `get_shop_data()` — `postgresql/run_query.py`
- `get_reviews`: `shop.map_id` 1:1 → `shop_id`·`shop_cd` (기존 `map_id` 복사 제거)
- 미매칭·다중 매칭: `PostAnalysisErrors.GetReviews.Warn` + 행 드랍
- MERGE SQL에 `shop_cd` 추가

## 실행 순서 (확정)

`pipeline.py` 또는 `get_reviews` → `analyze_sentimental` → `analyze_keywords_by_llm`

상세 설계: [design.md](design.md)
