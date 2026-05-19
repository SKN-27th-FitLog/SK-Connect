# post_analysis 리팩토링 이력

sk-connect-etl-standards Part A 기준으로 2026-05 구조 정리.  
오케스트레이션은 루트 스크립트 5개 유지(외부 스케줄러 연동 예정).

## Phase 1 — 인프라 분리

- `common/postgresql/` → 루트 `postgresql/` 승격
- DB 상수·MERGE SQL → `postgresql/config.py`
- `connection.py` `__main__` 제거 → `python -m postgresql`
- 루트 스크립트 import: `postgresql.run_query`

## Phase 2 — 에러 중앙화

- `common/errors.py` — `PostAnalysisErrors` (Sentiment, KiwiKeywords, LlmKeywords, ClassifyKeywords)
- 4개 배치 스크립트의 컬럼 누락 `ValueError` 통합

## Phase 3 — BERT 통합

- `analyze_sentimental.py` → `BertTokenizer` 사용, 모듈 import 시 모델 로드 제거
- `BertTokenizer`에 `Singleton` 적용

## Phase 4 — MERGE·스키마

- MERGE SQL에 `information_cd` 추가
- `get_reviews`: 식당 리뷰 적재 시 `information_cd=IC01` (`CodeTable.INFORMATION_RESTAURANT`)
- `WHEN MATCHED` UPDATE 전 컬럼 `COALESCE(x.col, a.col)` — 부분 MERGE NULL 덮어쓰기 방지

## Phase 5 — 운영 정리

- `classify_keywords`: `max_rows` 인자 추가, 기본 전량 처리 (`PREVIEW_MAX_ROWS=4` 제거)
- `common/env.py` — `load_dotenv` 일원화 (`postgresql/connection`, LLM 스크립트)
- `requirements.txt`: `python-dotenv`, `langchain-openai` pin; `dotenv` 패키지 제거
- `.gitignore`: `.venv`, `.env`, `__pycache__` 등

## 실행 순서 (참고)

`get_reviews` → `analyze_sentimental` → `analyze_keywords` 또는 `analyze_keywords_by_llm` → `classify_keywords`

상세 설계: [design.md](design.md)
