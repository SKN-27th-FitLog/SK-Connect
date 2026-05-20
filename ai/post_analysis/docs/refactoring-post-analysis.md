# post_analysis 리팩토링 이력

sk-connect-etl-standards Part A 기준으로 2026-05 구조 정리.  
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

## 실행 순서 (확정)

`get_reviews` → `analyze_sentimental` → `analyze_keywords_by_llm`

상세 설계: [design.md](design.md)
