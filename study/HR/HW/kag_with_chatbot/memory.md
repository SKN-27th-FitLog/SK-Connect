# memory.md

## Current State

이 프로젝트는 Streamlit 기반 개인화 맛집 추천 챗봇이다. 사용자는 자연어로 지역, 메뉴, 분위기, 제외 조건 등을 입력하고, LangGraph 워크플로우가 파싱, 추천, 검증, 응답 생성을 수행한다. 추천 데이터는 Neo4j 그래프 DB에서 조회되며, LLM은 Ollama 로컬 모델을 사용한다.

## Operating Context

- UI: Streamlit (`app.py`)
- Workflow: LangGraph + SQLite checkpoint (`core/graph.py`, `database/memory.py`)
- LLM: LangChain Ollama (`core/llm.py`)
- Database: Neo4j 5.23.0 (`docker-compose.yml`, `database/neo4j_client.py`)
- Data ingestion: pandas, KoNLPy Okt, Ollama (`ingestion/ingest_v2.py`)
- Tests: pytest (`tests/*`)

## Structure

- `app.py`: 사용자 입력, 세션 상태, 추천 결과 표시, 좋아요/싫어요 버튼
- `core/state.py`: AgentState 타입 계약
- `core/graph.py`: parser, clarifier, recommender, validator, generator, classifier, updater 노드 연결
- `core/nodes/*`: 각 LangGraph 노드 구현
- `recommendation/*`: Neo4j 쿼리 조립, 추천 엔진, 스코어링 후처리
- `knowledge/*`: 온톨로지, 우선순위, 정책, RULE.MD 로더
- `database/*`: Neo4j 클라이언트, SQLite 체크포인터, Cypher 스키마
- `ingestion/ingest_v2.py`: CSV 원본 데이터를 Neo4j에 적재

## Core Models / State

핵심 상태는 `AgentState`이며 세션, 사용자 입력, 검색 축, 제약/선호, 온톨로지 키워드, 운영 모드, 재질의 상태, 추천 결과, 피드백 정보를 담는다. `chat_history`는 LangGraph 병합 전략으로 누적된다.

Neo4j 모델은 `Restaurant`, `Area`, `Tag`, `User` 노드와 `LOCATED_IN`, `BELONGS_TO`, `HAS_TAG`, `INTERACTED`, `DISLIKES` 관계를 중심으로 구성된다.

## Decisions and Conventions

- LLM은 추출/분류용 `llm_extra`와 응답 생성용 `llm_chat`으로 분리한다.
- 검색은 Strict, Ontology Expansion, Soft Relaxation 워터폴 전략을 사용한다.
- 온톨로지 계층으로 메뉴/광의 의도/유의어/지명 검증을 결정론적으로 보완한다.
- 추천 결과는 Neo4j query score 이후 Python 후처리로 다양성, 중복 제거, 결정론적 정렬을 적용한다.
- 행동 규칙은 `RULE.MD`에서 섹션별로 읽어 LLM 프롬프트에 삽입한다.

## Known Issues and Risks

- `app.py` 초기 상태와 `AgentState` 필드가 일부 불일치한다.
- `payload`, `keyword_intent`, `dietary_constraints` 같은 필드가 타입 계약과 노드 간 사용에서 일관되지 않다.
- validator의 ABSOLUTE 사후 검증은 `keyword_intent`가 채워지지 않으면 작동하지 않을 수 있다.
- generator는 `state.ui_mode`보다 `payload.ui_mode`를 읽어 RELAXATION_PROPOSAL 전환을 놓칠 수 있다.
- LIKE/DISLIKE 저장 메서드는 있으나 피드백 노드와 UI 흐름에 완전히 연결되어 있지 않다.
- 대화 초기화 시 `viewed_ids`가 초기화되지 않는다.
- Neo4j/Ollama/Java 의존성이 충족되지 않으면 추천 또는 적재가 조용히 실패할 수 있다.

## Next Actions

1. `AgentState`와 `app.py` 초기 상태를 동기화한다.
2. `payload`, `keyword_intent`, `dietary_constraints` 필드 명칭과 흐름을 정리한다.
3. validator와 generator의 모드 전환 경로를 end-to-end로 검증한다.
4. LIKE/DISLIKE 피드백을 Neo4j 저장 로직에 연결한다.
5. LangGraph 통합 테스트와 Neo4j 쿼리 빌더 테스트를 추가한다.
