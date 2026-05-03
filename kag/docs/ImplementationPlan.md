# KAG Graph DB Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `docs/Design.md`의 설계를 기준으로 맛집/IT 뉴스 도메인을 Neo4j 그래프 DB와 Python QueryBuilder로 검증 가능한 최소 KAG 구조로 구현한다.

**Architecture:** 하나의 Neo4j DB 안에 맛집과 IT 뉴스 도메인을 구성하되, 도메인별 핵심 노드와 관계는 분리한다. 사용자 발화는 `Domain -> Intent -> Slot -> Query Template -> Neo4j Path -> LLM Path Interpreter` 흐름으로 처리하며, LLM은 Cypher를 생성하지 않고 반환된 evidence path만 해석한다.

**Tech Stack:** Python 3.11+, Neo4j, Cypher, pytest, python-dotenv, neo4j Python driver

---

## 구현 기준

- `Restaurant`와 `NewsArticle`은 직접 연결하지 않는다.
- 도메인 간 느슨한 연결은 `Concept` 노드로만 처리한다.
- 검색은 Property 조건보다 Relationship 탐색을 우선한다.
- `Full-text Search`는 후보 노드 탐색용 fallback으로만 사용한다.
- MVP 단계의 Query Template은 read-only로 유지한다. Query 실행 중 `UserIntent` 노드나 관계를 `MERGE`/`CREATE`하지 않는다.
- `EXCLUDES`는 문자열 필터가 아니라 Slot/Parameter의 명시적 부정 조건으로 처리하고, 실제 제외 효과는 그래프 관계 탐색으로 검증한다.
- `UserIntent -[:EXCLUDES]-> Ingredient/Menu/Tag/Concept` 같은 Intent Graph 저장은 서비스 확장 단계의 별도 write stage에서만 도입한다.
- MVP 테스트는 `EXCLUDES` 관계 생성 여부를 검증하지 않는다. 대신 negative Slot이 Query Parameter로 분리되고, `NOT EXISTS` 관계 탐색으로 제외 대상이 결과에서 빠지는지를 검증한다.
- QueryBuilder는 Cypher 문자열을 조합하지 않고 템플릿 선택과 파라미터 생성만 수행한다.
- Slot 값은 `normalized_value`만 쿼리 파라미터에 사용한다.
- Slot normalization 실패 시 QueryBuilder로 바로 넘기지 않고 `SlotNormalizer`가 full-text fallback으로 후보 노드를 찾은 뒤 정규화한다.
- Neo4j Repository는 `record.data()`를 그대로 반환하지 않고 LLM 해석에 맞는 Path DTO로 변환한다.
- 자연어 전처리는 `Rule-first LLM-assisted NLP Pipeline`으로 구현한다. Rule 기반 분류/추출을 먼저 수행하고, confidence가 낮거나 Slot이 부족한 경우에만 LLM Assist가 후보를 제안한다.
- LLM Assist 결과는 `SlotValidator`를 통과해야만 `SlotNormalizer`와 `GraphQueryBuilder`로 전달한다.
- LLM Assist는 Cypher 생성, Query Template 직접 선택, Neo4j 검색 실행, DB 결과 생성을 하지 않는다.

## 파일 구조

- Create: `pyproject.toml` - 패키지 의존성과 pytest 설정
- Create: `.env.example` - Neo4j 접속 환경 변수 예시
- Create: `src/kag_graph/models.py` - 공통 데이터 모델
- Create: `src/kag_graph/constants.py` - 도메인, Intent, 템플릿 이름 상수
- Create: `src/kag_graph/domain_classifier.py` - raw_text의 도메인 분류
- Create: `src/kag_graph/intent_classifier.py` - 도메인별 Intent 분류
- Create: `src/kag_graph/slot_extractor.py` - raw_text에서 Slot 추출
- Create: `src/kag_graph/llm_assist.py` - 낮은 confidence 결과에 대한 LLM 후보 제안 인터페이스
- Create: `src/kag_graph/slot_validator.py` - Slot/Intent/Template 요구사항 검증
- Create: `src/kag_graph/nlp_pipeline.py` - Domain/Intent/Slot/Validator/Normalizer 전처리 통합
- Create: `src/kag_graph/slot_normalizer.py` - Slot 정규화 및 full-text fallback 후보 탐색
- Create: `src/kag_graph/query_repository.py` - `.cypher` 템플릿 로더
- Create: `src/kag_graph/query_builder.py` - Intent/Slot 기반 템플릿 선택과 파라미터 생성
- Create: `src/kag_graph/pipeline.py` - Clarification 대상 요청을 Query 실행 전에 중단
- Create: `src/kag_graph/neo4j_repository.py` - Neo4j 실행 및 path 결과 변환
- Create: `src/kag_graph/interpreter.py` - evidence path 기반 응답 해석 인터페이스
- Create: `queries/schema/constraints.cypher` - 제약조건과 일반 인덱스
- Create: `queries/schema/fulltext_indexes.cypher` - full-text 인덱스
- Create: `queries/seed/restaurant.cypher` - 맛집 샘플 노드/관계
- Create: `queries/seed/news.cypher` - IT 뉴스 샘플 노드/관계
- Create: `queries/seed/common.cypher` - Concept 샘플 및 도메인 간 느슨한 연결
- Create: `queries/restaurant/*.cypher` - 맛집 Query Template
- Create: `queries/news/*.cypher` - IT 뉴스 Query Template
- Create: `queries/common/*.cypher` - Concept bridge 및 fallback Query Template
- Create: `tests/test_domain_classifier.py` - 도메인 분류 테스트
- Create: `tests/test_intent_classifier.py` - Intent 분류 테스트
- Create: `tests/test_slot_extractor.py` - Slot 추출 테스트
- Create: `tests/test_llm_assist.py` - LLM Assist 경계 테스트
- Create: `tests/test_slot_validator.py` - Slot 검증 테스트
- Create: `tests/test_nlp_pipeline.py` - 자연어 전처리 통합 테스트
- Create: `tests/test_query_builder.py` - 템플릿 선택/파라미터 생성 단위 테스트
- Create: `tests/test_query_repository.py` - 쿼리 템플릿 로딩 테스트
- Create: `tests/test_scenarios.py` - 설계서 TEST-R/N/M 시나리오 검증

---

## Task 1: Python 프로젝트 스캐폴딩

**Files:**
- Create: `pyproject.toml`
- Create: `.env.example`
- Create: `src/kag_graph/__init__.py`

- [ ] **Step 1: 프로젝트 설정 파일 작성**

`pyproject.toml`:

```toml
[project]
name = "kag-graph"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
  "neo4j>=5.20.0",
  "python-dotenv>=1.0.1"
]

[project.optional-dependencies]
test = [
  "pytest>=8.2.0"
]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
```

`.env.example`:

```bash
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password
NEO4J_DATABASE=neo4j
```

- [ ] **Step 2: 패키지 초기화 파일 생성**

`src/kag_graph/__init__.py`:

```python
"""KAG graph search package."""
```

- [ ] **Step 3: 기본 테스트 실행**

Run: `python -m pytest`

Expected: 테스트가 아직 없으면 `no tests ran` 또는 수집된 테스트 0개로 종료한다.

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml .env.example src/kag_graph/__init__.py
git commit -m "chore: scaffold kag graph project"
```

---

## Task 2: 공통 모델과 상수 정의

**Files:**
- Create: `src/kag_graph/models.py`
- Create: `src/kag_graph/constants.py`
- Test: `tests/test_query_builder.py`

- [ ] **Step 1: 실패하는 모델 테스트 작성**

`tests/test_query_builder.py`:

```python
from kag_graph.constants import Domain, Intent, TemplateName
from kag_graph.models import ExtractedSlot


def test_extracted_slot_uses_normalized_value_for_query_value():
    slot = ExtractedSlot(
        slot_type="positive_condition",
        node_label="Menu",
        raw_value="중국집",
        normalized_value="중국음식",
        confidence=0.95,
        is_negative=False,
        is_required=True,
    )

    assert slot.query_value == "중국음식"


def test_constants_include_priority_templates():
    assert Domain.RESTAURANT == "restaurant"
    assert Domain.MIXED == "mixed"
    assert Intent.RESTAURANT_EXCLUSION_SEARCH == "restaurant_exclusion_search"
    assert TemplateName.RESTAURANT_MENU_EXCLUDE_INGREDIENT == "restaurant_menu_exclude_ingredient"
    assert TemplateName.NEWS_AUDIENCE_FILTER == "news_audience_filter"
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `python -m pytest tests/test_query_builder.py -v`

Expected: `ModuleNotFoundError` 또는 `ImportError`

- [ ] **Step 3: 모델과 상수 구현**

`src/kag_graph/constants.py`:

```python
class Domain:
    RESTAURANT = "restaurant"
    IT_NEWS = "it_news"
    MIXED = "mixed"
    UNKNOWN = "unknown"


class Intent:
    RESTAURANT_RECOMMENDATION = "restaurant_recommendation"
    RESTAURANT_EXCLUSION_SEARCH = "restaurant_exclusion_search"
    RESTAURANT_CONTEXT_RECOMMENDATION = "restaurant_context_recommendation"
    RESTAURANT_PRICE_FILTER = "restaurant_price_filter"
    RESTAURANT_AREA_SEARCH = "restaurant_area_search"
    NEWS_SUMMARY = "news_summary"
    NEWS_TREND_ANALYSIS = "news_trend_analysis"
    NEWS_EVENT_SEARCH = "news_event_search"
    NEWS_COMPARISON = "news_comparison"
    NEWS_AUDIENCE_FILTER = "news_audience_filter"
    CONCEPT_BRIDGE_SEARCH = "concept_bridge_search"
    CLARIFICATION_REQUIRED = "clarification_required"
    UNSUPPORTED_REQUEST = "unsupported_request"


class TemplateName:
    RESTAURANT_AREA_MENU_TAG = "restaurant_area_menu_tag"
    RESTAURANT_MENU_ONLY = "restaurant_menu_only"
    RESTAURANT_MENU_EXCLUDE_INGREDIENT = "restaurant_menu_exclude_ingredient"
    RESTAURANT_MENU_EXCLUDE_INGREDIENT_MENU_LEVEL = "restaurant_menu_exclude_ingredient_menu_level"
    RESTAURANT_MENU_REQUIRED_TAG_EXCLUDE_TAG = "restaurant_menu_required_tag_exclude_tag"
    RESTAURANT_MENU_TAG_PRICE = "restaurant_menu_tag_price"
    RESTAURANT_CONTEXT_TAGS = "restaurant_context_tags"
    RESTAURANT_TAG_ONLY = "restaurant_tag_only"
    NEWS_TOPIC_SEARCH = "news_topic_search"
    NEWS_TECH_EVENT_SEARCH = "news_tech_event_search"
    NEWS_COMPANY_COMPARISON = "news_company_comparison"
    NEWS_TOPIC_EVENT_SEARCH = "news_topic_event_search"
    NEWS_AUDIENCE_FILTER = "news_audience_filter"
    CONCEPT_BRIDGE_SEARCH = "concept_bridge_search"
    FOOD_CONDITION_FULLTEXT_SEARCH = "food_condition_fulltext_search"
    NEWS_CONDITION_FULLTEXT_SEARCH = "news_condition_fulltext_search"
    NEWS_TEXT_FULLTEXT_SEARCH = "news_text_fulltext_search"
```

`src/kag_graph/models.py`:

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class ClassificationResult:
    value: str
    confidence: float
    reason: str
    needs_llm_assist: bool = False


@dataclass(frozen=True)
class ExtractedSlot:
    slot_type: str
    node_label: str
    raw_value: str
    normalized_value: str
    confidence: float
    is_negative: bool
    is_required: bool

    @property
    def query_value(self) -> str:
        return self.normalized_value


@dataclass(frozen=True)
class QueryBuildResult:
    template_name: str
    query_text: str
    params: dict[str, object]
    expected_path_pattern: str


@dataclass(frozen=True)
class GraphNodeDTO:
    labels: list[str]
    properties: dict[str, object]


@dataclass(frozen=True)
class GraphRelationshipDTO:
    type: str
    start_node: GraphNodeDTO
    end_node: GraphNodeDTO
    properties: dict[str, object]


@dataclass(frozen=True)
class EvidencePathDTO:
    nodes: list[GraphNodeDTO]
    relationships: list[GraphRelationshipDTO]


@dataclass(frozen=True)
class GraphSearchResultDTO:
    result_node: GraphNodeDTO
    evidence_paths: list[EvidencePathDTO]
    score: float


@dataclass(frozen=True)
class ValidationResult:
    is_valid: bool
    slots: list[ExtractedSlot]
    status: str
    message: str | None = None
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `python -m pytest tests/test_query_builder.py -v`

Expected: `2 passed`

- [ ] **Step 5: Commit**

```bash
git add src/kag_graph/models.py src/kag_graph/constants.py tests/test_query_builder.py
git commit -m "feat: define graph query models"
```

---

## Task 3: Neo4j 스키마 Cypher 작성

**Files:**
- Create: `queries/schema/constraints.cypher`
- Create: `queries/schema/fulltext_indexes.cypher`

- [ ] **Step 1: 제약조건과 인덱스 작성**

`queries/schema/constraints.cypher`:

```cypher
CREATE CONSTRAINT restaurant_id IF NOT EXISTS
FOR (n:Restaurant) REQUIRE n.restaurant_id IS UNIQUE;

CREATE CONSTRAINT area_normalized_name IF NOT EXISTS
FOR (n:Area) REQUIRE n.normalized_name IS UNIQUE;

CREATE CONSTRAINT menu_normalized_name IF NOT EXISTS
FOR (n:Menu) REQUIRE n.normalized_name IS UNIQUE;

CREATE CONSTRAINT ingredient_normalized_name IF NOT EXISTS
FOR (n:Ingredient) REQUIRE n.normalized_name IS UNIQUE;

CREATE CONSTRAINT tag_normalized_name IF NOT EXISTS
FOR (n:Tag) REQUIRE n.normalized_name IS UNIQUE;

CREATE CONSTRAINT news_article_id IF NOT EXISTS
FOR (n:NewsArticle) REQUIRE n.article_id IS UNIQUE;

CREATE CONSTRAINT topic_normalized_name IF NOT EXISTS
FOR (n:Topic) REQUIRE n.normalized_name IS UNIQUE;

CREATE CONSTRAINT technology_normalized_name IF NOT EXISTS
FOR (n:Technology) REQUIRE n.normalized_name IS UNIQUE;

CREATE CONSTRAINT company_normalized_name IF NOT EXISTS
FOR (n:Company) REQUIRE n.normalized_name IS UNIQUE;

CREATE CONSTRAINT event_normalized_name IF NOT EXISTS
FOR (n:Event) REQUIRE n.normalized_name IS UNIQUE;

CREATE CONSTRAINT concept_normalized_name IF NOT EXISTS
FOR (n:Concept) REQUIRE n.normalized_name IS UNIQUE;

CREATE INDEX restaurant_rating IF NOT EXISTS
FOR (n:Restaurant) ON (n.rating);

CREATE INDEX restaurant_avg_price IF NOT EXISTS
FOR (n:Restaurant) ON (n.avg_price);

CREATE INDEX news_published_at IF NOT EXISTS
FOR (n:NewsArticle) ON (n.published_at);
```

- [ ] **Step 2: Full-text 인덱스 작성**

`queries/schema/fulltext_indexes.cypher`:

```cypher
CREATE FULLTEXT INDEX restaurant_text_index IF NOT EXISTS
FOR (n:Restaurant) ON EACH [n.name, n.description, n.address];

CREATE FULLTEXT INDEX food_condition_text_index IF NOT EXISTS
FOR (n:Menu|Ingredient|Tag) ON EACH [n.name, n.normalized_name];

CREATE FULLTEXT INDEX news_text_index IF NOT EXISTS
FOR (n:NewsArticle) ON EACH [n.title, n.summary, n.content];

CREATE FULLTEXT INDEX news_condition_text_index IF NOT EXISTS
FOR (n:Topic|Technology|Company|Event) ON EACH [n.name, n.normalized_name];
```

- [ ] **Step 3: Neo4j에서 스키마 적용**

Run: `cypher-shell -u neo4j -p password -f queries/schema/constraints.cypher`

Expected: 오류 없이 완료

Run: `cypher-shell -u neo4j -p password -f queries/schema/fulltext_indexes.cypher`

Expected: 오류 없이 완료

- [ ] **Step 4: Commit**

```bash
git add queries/schema/constraints.cypher queries/schema/fulltext_indexes.cypher
git commit -m "feat: add neo4j schema constraints"
```

---

## Task 4: 샘플 그래프 데이터 작성

**Files:**
- Create: `queries/seed/restaurant.cypher`
- Create: `queries/seed/news.cypher`
- Create: `queries/seed/common.cypher`

- [ ] **Step 1: 맛집 샘플 데이터 작성**

핵심 포함 조건:
- `Restaurant` 8개
- `Area` 6개
- `Menu` 12개
- `Ingredient` 5개
- `Tag` 14개
- `Restaurant -[:SELLS]-> Menu`
- `Menu -[:CONTAINS]-> Ingredient`
- `Restaurant -[:HAS_TAG]-> Tag`
- `Restaurant -[:LOCATED_IN]-> Area`
- 테스트 기대 결과가 어긋나지 않도록 Design.md의 샘플 이름을 그대로 사용한다.
  - `강남파스타`
  - `조용한카페`
  - `홍콩반점`
  - `담백한고기집`

대표 검증 데이터는 반드시 포함한다.

```cypher
MERGE (r:Restaurant {restaurant_id: "R001"})
SET r.name = "홍콩반점",
    r.avg_price = 12000,
    r.rating = 4.1,
    r.description = "중국음식 식당이며 짜장면과 짬뽕처럼 면이 포함된 메뉴를 판매하는 식당",
    r.is_active = true;

MERGE (m:Menu {normalized_name: "중국음식"})
SET m.menu_id = "M001", m.name = "중국음식", m.menu_type = "category";

MERGE (rice:Menu {normalized_name: "볶음밥"})
SET rice.menu_id = "M002", rice.name = "볶음밥", rice.menu_type = "dish", rice.price = 10000;

MERGE (noodle:Ingredient {normalized_name: "면"})
SET noodle.ingredient_id = "I001", noodle.name = "면";

MERGE (r)-[:SELLS]->(m);
MERGE (r)-[:SELLS]->(rice);
```

- [ ] **Step 2: IT 뉴스 샘플 데이터 작성**

대표 검증 데이터는 반드시 포함한다.

```cypher
MERGE (a:NewsArticle {article_id: "A001"})
SET a.title = "GPT 업데이트 공개",
    a.summary = "새 GPT 업데이트가 개발자 기능과 응답 품질을 개선했다.",
    a.published_at = date("2026-05-01"),
    a.source = "sample",
    a.url = "https://example.com/news/a001";

MERGE (t:Technology {normalized_name: "gpt"})
SET t.technology_id = "TECH001", t.name = "GPT", t.technology_type = "ai_model";

MERGE (e:Event {normalized_name: "업데이트"})
SET e.event_id = "E001", e.name = "업데이트", e.event_type = "release";

MERGE (a)-[:MENTIONS_TECH]->(t);
MERGE (a)-[:DESCRIBES_EVENT]->(e);
```

- [ ] **Step 3: 공통 Concept 샘플 작성**

```cypher
MERGE (c:Concept {normalized_name: "ai"})
SET c.concept_id = "C001", c.name = "AI", c.concept_type = "cross_domain";

MATCH (t:Technology {normalized_name: "gpt"})
MERGE (t)-[:RELATED_TO]->(c);

MATCH (a:NewsArticle {article_id: "A001"})
MERGE (a)-[:RELATED_TO]->(c);
```

- [ ] **Step 4: 샘플 데이터 적재**

Run: `cypher-shell -u neo4j -p password -f queries/seed/restaurant.cypher`

Expected: 오류 없이 완료

Run: `cypher-shell -u neo4j -p password -f queries/seed/news.cypher`

Expected: 오류 없이 완료

Run: `cypher-shell -u neo4j -p password -f queries/seed/common.cypher`

Expected: 오류 없이 완료

- [ ] **Step 5: Commit**

```bash
git add queries/seed/restaurant.cypher queries/seed/news.cypher queries/seed/common.cypher
git commit -m "feat: add sample graph seed data"
```

---

## Task 5: DomainClassifier 구현

**Files:**
- Create: `src/kag_graph/domain_classifier.py`
- Test: `tests/test_domain_classifier.py`

- [ ] **Step 1: 도메인 분류 테스트 작성**

`tests/test_domain_classifier.py`:

```python
from kag_graph.constants import Domain
from kag_graph.domain_classifier import DomainClassifier


def test_domain_classifier_detects_restaurant():
    result = DomainClassifier().classify("강남 맛집 추천해줘")

    assert result.value == Domain.RESTAURANT
    assert result.confidence >= 0.7


def test_domain_classifier_detects_it_news():
    result = DomainClassifier().classify("GPT 업데이트 알려줘")

    assert result.value == Domain.IT_NEWS
    assert result.confidence >= 0.7


def test_domain_classifier_detects_mixed():
    result = DomainClassifier().classify("판교 맛집이랑 판교 IT 뉴스 같이 보고 싶어")

    assert result.value == Domain.MIXED
    assert result.confidence >= 0.7


def test_domain_classifier_marks_unknown_for_ambiguous_text():
    result = DomainClassifier().classify("요즘 뭐가 좋아?")

    assert result.value == Domain.UNKNOWN
    assert result.needs_llm_assist is True
```

- [ ] **Step 2: DomainClassifier 구현**

`src/kag_graph/domain_classifier.py`:

```python
from kag_graph.constants import Domain
from kag_graph.models import ClassificationResult


class DomainClassifier:
    RESTAURANT_KEYWORDS = {"맛집", "식당", "카페", "밥집", "메뉴", "음식", "회식", "혼밥", "배달", "가격", "강남", "홍대"}
    IT_NEWS_KEYWORDS = {"뉴스", "기사", "GPT", "AI", "클라우드", "보안", "업데이트", "투자", "규제", "삼성", "애플", "OpenAI", "Microsoft", "Google"}

    def classify(self, raw_text: str) -> ClassificationResult:
        restaurant_score = self._keyword_score(raw_text, self.RESTAURANT_KEYWORDS)
        news_score = self._keyword_score(raw_text, self.IT_NEWS_KEYWORDS)

        if restaurant_score > 0 and news_score > 0:
            return ClassificationResult(Domain.MIXED, 0.85, "restaurant and it_news keywords matched")

        if restaurant_score > 0:
            return ClassificationResult(Domain.RESTAURANT, 0.8, "restaurant keywords matched")

        if news_score > 0:
            return ClassificationResult(Domain.IT_NEWS, 0.8, "it_news keywords matched")

        return ClassificationResult(Domain.UNKNOWN, 0.0, "no domain keyword matched", needs_llm_assist=True)

    def _keyword_score(self, raw_text: str, keywords: set[str]) -> int:
        return sum(1 for keyword in keywords if keyword in raw_text)
```

- [ ] **Step 3: 테스트 실행**

Run: `python -m pytest tests/test_domain_classifier.py -v`

Expected: `4 passed`

- [ ] **Step 4: Commit**

```bash
git add src/kag_graph/domain_classifier.py tests/test_domain_classifier.py
git commit -m "feat: add rule first domain classifier"
```

---

## Task 6: IntentClassifier 구현

**Files:**
- Create: `src/kag_graph/intent_classifier.py`
- Test: `tests/test_intent_classifier.py`

- [ ] **Step 1: Intent 분류 테스트 작성**

`tests/test_intent_classifier.py`:

```python
from kag_graph.constants import Domain, Intent
from kag_graph.intent_classifier import IntentClassifier


def test_intent_classifier_detects_restaurant_exclusion():
    result = IntentClassifier().classify("면은 싫은데 중국집 가고 싶어", Domain.RESTAURANT)

    assert result.value == Intent.RESTAURANT_EXCLUSION_SEARCH


def test_intent_classifier_detects_price_filter():
    result = IntentClassifier().classify("1만원 이하 한식집 알려줘", Domain.RESTAURANT)

    assert result.value == Intent.RESTAURANT_PRICE_FILTER


def test_intent_classifier_detects_news_event():
    result = IntentClassifier().classify("GPT 업데이트 알려줘", Domain.IT_NEWS)

    assert result.value == Intent.NEWS_EVENT_SEARCH


def test_intent_classifier_detects_news_comparison():
    result = IntentClassifier().classify("삼성과 애플 비교해줘", Domain.IT_NEWS)

    assert result.value == Intent.NEWS_COMPARISON
```

- [ ] **Step 2: IntentClassifier 구현**

`src/kag_graph/intent_classifier.py`:

```python
from kag_graph.constants import Domain, Intent
from kag_graph.models import ClassificationResult


class IntentClassifier:
    def classify(self, raw_text: str, domain: str) -> ClassificationResult:
        if domain == Domain.MIXED and "같이" in raw_text:
            return ClassificationResult(Intent.CONCEPT_BRIDGE_SEARCH, 0.85, "mixed concept bridge request")

        if domain == Domain.RESTAURANT:
            if any(token in raw_text for token in ("싫어", "말고", "제외", "빼줘", "안 들어간", "피하고 싶어")):
                return ClassificationResult(Intent.RESTAURANT_EXCLUSION_SEARCH, 0.9, "negative restaurant condition")
            if any(token in raw_text for token in ("1만원", "2만원", "저렴한", "가격", "가성비")):
                return ClassificationResult(Intent.RESTAURANT_PRICE_FILTER, 0.85, "restaurant price condition")
            return ClassificationResult(Intent.RESTAURANT_RECOMMENDATION, 0.75, "default restaurant recommendation")

        if domain == Domain.IT_NEWS:
            if any(token in raw_text for token in ("비교", "vs", "경쟁", "차이")):
                return ClassificationResult(Intent.NEWS_COMPARISON, 0.85, "news comparison expression")
            if any(token in raw_text for token in ("업데이트", "사고", "규제", "투자", "출시")):
                return ClassificationResult(Intent.NEWS_EVENT_SEARCH, 0.85, "news event expression")
            return ClassificationResult(Intent.NEWS_SUMMARY, 0.75, "default news summary")

        return ClassificationResult(Intent.CLARIFICATION_REQUIRED, 0.0, "unsupported or unknown domain", needs_llm_assist=True)
```

- [ ] **Step 3: 테스트 실행**

Run: `python -m pytest tests/test_intent_classifier.py -v`

Expected: `4 passed`

- [ ] **Step 4: Commit**

```bash
git add src/kag_graph/intent_classifier.py tests/test_intent_classifier.py
git commit -m "feat: add rule first intent classifier"
```

---

## Task 7: SlotExtractor 구현

**Files:**
- Create: `src/kag_graph/slot_extractor.py`
- Test: `tests/test_slot_extractor.py`

- [ ] **Step 1: Slot 추출 테스트 작성**

`tests/test_slot_extractor.py`:

```python
from kag_graph.constants import Domain, Intent
from kag_graph.slot_extractor import SlotExtractor


def test_slot_extractor_extracts_restaurant_exclusion_slots():
    slots = SlotExtractor().extract("면은 싫은데 중국집 가고 싶어", Domain.RESTAURANT, Intent.RESTAURANT_EXCLUSION_SEARCH)

    assert any(slot.node_label == "Menu" and slot.normalized_value == "중국음식" and not slot.is_negative for slot in slots)
    assert any(slot.node_label == "Ingredient" and slot.normalized_value == "면" and slot.is_negative for slot in slots)


def test_slot_extractor_extracts_news_event_slots():
    slots = SlotExtractor().extract("최근 GPT 관련 업데이트 알려줘", Domain.IT_NEWS, Intent.NEWS_EVENT_SEARCH)

    assert any(slot.node_label == "Technology" and slot.normalized_value == "gpt" for slot in slots)
    assert any(slot.node_label == "Event" and slot.normalized_value == "업데이트" for slot in slots)


def test_slot_extractor_extracts_positive_and_negative_tags():
    slots = SlotExtractor().extract("시끄러운 곳 말고 조용한 카페 알려줘", Domain.RESTAURANT, Intent.RESTAURANT_EXCLUSION_SEARCH)

    assert any(slot.node_label == "Menu" and slot.normalized_value == "카페" for slot in slots)
    assert any(slot.node_label == "Tag" and slot.normalized_value == "조용한" and not slot.is_negative for slot in slots)
    assert any(slot.node_label == "Tag" and slot.normalized_value == "시끄러운" and slot.is_negative for slot in slots)
```

- [ ] **Step 2: SlotExtractor 구현**

`src/kag_graph/slot_extractor.py`:

```python
from kag_graph.models import ExtractedSlot


class SlotExtractor:
    def extract(self, raw_text: str, domain: str, intent: str) -> list[ExtractedSlot]:
        slots: list[ExtractedSlot] = []

        if "중국집" in raw_text or "중국음식" in raw_text:
            slots.append(ExtractedSlot("positive_condition", "Menu", "중국집", "중국음식", 0.9, False, True))
        if "카페" in raw_text:
            slots.append(ExtractedSlot("positive_condition", "Menu", "카페", "카페", 0.9, False, True))
        if "면" in raw_text and any(token in raw_text for token in ("싫", "말고", "제외", "빼줘")):
            slots.append(ExtractedSlot("negative_condition", "Ingredient", "면", "면", 0.9, True, True))
        if "조용한" in raw_text:
            slots.append(ExtractedSlot("positive_condition", "Tag", "조용한", "조용한", 0.9, False, True))
        if "시끄러운" in raw_text and any(token in raw_text for token in ("말고", "싫", "제외", "빼줘")):
            slots.append(ExtractedSlot("negative_condition", "Tag", "시끄러운", "시끄러운", 0.9, True, True))
        if "GPT" in raw_text:
            slots.append(ExtractedSlot("positive_condition", "Technology", "GPT", "gpt", 0.9, False, True))
        if "업데이트" in raw_text:
            slots.append(ExtractedSlot("event", "Event", "업데이트", "업데이트", 0.9, False, True))
        if "판교" in raw_text:
            slots.append(ExtractedSlot("concept", "Concept", "판교", "판교", 0.9, False, True))

        return slots
```

- [ ] **Step 3: 테스트 실행**

Run: `python -m pytest tests/test_slot_extractor.py -v`

Expected: `3 passed`

- [ ] **Step 4: Commit**

```bash
git add src/kag_graph/slot_extractor.py tests/test_slot_extractor.py
git commit -m "feat: extract graph search slots"
```

---

## Task 8: LLM Assist Interface 구현

**Files:**
- Create: `src/kag_graph/llm_assist.py`
- Test: `tests/test_llm_assist.py`

- [ ] **Step 1: LLM Assist 경계 테스트 작성**

`tests/test_llm_assist.py`:

```python
from kag_graph.llm_assist import LLMAssistResult


def test_llm_assist_result_is_candidate_only():
    result = LLMAssistResult(
        candidates=[{"node_label": "Menu", "raw_value": "중국집", "candidate_value": "중국음식", "confidence": 0.81}],
        confidence=0.81,
        reason="candidate suggestion",
        needs_clarification=False,
    )

    assert result.candidates[0]["candidate_value"] == "중국음식"
    assert not hasattr(result, "cypher")
```

- [ ] **Step 2: LLM Assist 인터페이스 구현**

`src/kag_graph/llm_assist.py`:

```python
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class LLMAssistResult:
    candidates: list[dict[str, object]]
    confidence: float
    reason: str
    needs_clarification: bool


class LLMAssist(Protocol):
    def suggest_domain(self, raw_text: str) -> LLMAssistResult:
        pass

    def suggest_intent(self, raw_text: str, domain: str) -> LLMAssistResult:
        pass

    def suggest_slots(self, raw_text: str, domain: str, intent: str) -> LLMAssistResult:
        pass
```

- [ ] **Step 3: 테스트 실행**

Run: `python -m pytest tests/test_llm_assist.py -v`

Expected: `1 passed`

- [ ] **Step 4: Commit**

```bash
git add src/kag_graph/llm_assist.py tests/test_llm_assist.py
git commit -m "feat: define llm assist candidate interface"
```

---

## Task 9: SlotValidator 구현

**Files:**
- Create: `src/kag_graph/slot_validator.py`
- Test: `tests/test_slot_validator.py`

- [ ] **Step 1: Slot 검증 테스트 작성**

`tests/test_slot_validator.py`:

```python
from kag_graph.constants import Intent
from kag_graph.models import ExtractedSlot
from kag_graph.slot_validator import SlotValidator


def test_slot_validator_accepts_required_restaurant_exclusion_slots():
    slots = [
        ExtractedSlot("positive_condition", "Menu", "중국집", "중국음식", 0.9, False, True),
        ExtractedSlot("negative_condition", "Ingredient", "면", "면", 0.9, True, True),
    ]

    result = SlotValidator().validate(Intent.RESTAURANT_EXCLUSION_SEARCH, slots)

    assert result.is_valid is True


def test_slot_validator_blocks_missing_required_slot():
    slots = [ExtractedSlot("positive_condition", "Menu", "중국집", "중국음식", 0.9, False, True)]

    result = SlotValidator().validate(Intent.RESTAURANT_EXCLUSION_SEARCH, slots)

    assert result.is_valid is False
    assert result.status == "clarification_required"


def test_slot_validator_blocks_low_confidence_slot():
    slots = [
        ExtractedSlot("positive_condition", "Technology", "GPT", "gpt", 0.6, False, True),
        ExtractedSlot("event", "Event", "업데이트", "업데이트", 0.9, False, True),
    ]

    result = SlotValidator().validate(Intent.NEWS_EVENT_SEARCH, slots)

    assert result.is_valid is False
```

- [ ] **Step 2: SlotValidator 구현**

`src/kag_graph/slot_validator.py`:

```python
from kag_graph.constants import Intent
from kag_graph.models import ExtractedSlot, ValidationResult


class SlotValidator:
    REQUIRED_SLOTS = {
        Intent.RESTAURANT_EXCLUSION_SEARCH: [("Menu", False), ("Ingredient", True)],
        Intent.NEWS_EVENT_SEARCH: [("Technology", False), ("Event", False)],
        Intent.CONCEPT_BRIDGE_SEARCH: [("Concept", False)],
    }
    ALLOWED_NODE_LABELS = {
        "Area", "Menu", "Ingredient", "Tag", "PriceCondition", "CapacityCondition", "Context",
        "Topic", "Technology", "Company", "Event", "Audience", "TimeCondition",
        "Concept", "NegativeCondition", "ComparisonTarget",
    }

    def validate(self, intent: str, slots: list[ExtractedSlot]) -> ValidationResult:
        for slot in slots:
            if slot.node_label not in self.ALLOWED_NODE_LABELS:
                return ValidationResult(False, slots, "clarification_required", f"unsupported slot label: {slot.node_label}")
            if slot.confidence < 0.7:
                return ValidationResult(False, slots, "clarification_required", f"low confidence slot: {slot.raw_value}")

        required_slots = self.REQUIRED_SLOTS.get(intent, [])
        for node_label, is_negative in required_slots:
            if not any(slot.node_label == node_label and slot.is_negative is is_negative for slot in slots):
                return ValidationResult(False, slots, "clarification_required", f"missing required slot: {node_label}")

        return ValidationResult(True, slots, "validated")
```

- [ ] **Step 3: 테스트 실행**

Run: `python -m pytest tests/test_slot_validator.py -v`

Expected: `3 passed`

- [ ] **Step 4: Commit**

```bash
git add src/kag_graph/slot_validator.py tests/test_slot_validator.py
git commit -m "feat: validate slots before query building"
```

## Task 10: SlotNormalizer와 full-text fallback 설계

**Files:**
- Create: `src/kag_graph/slot_normalizer.py`
- Test: `tests/test_slot_normalizer.py`

- [ ] **Step 1: 정규화 실패 시 fallback 후보를 요청하는 테스트 작성**

`tests/test_slot_normalizer.py`:

```python
from kag_graph.models import ExtractedSlot
from kag_graph.slot_normalizer import SlotNormalizer


class FakeFallbackSearch:
    def find_candidate(self, node_label: str, raw_value: str) -> str | None:
        if node_label == "Menu" and raw_value == "중국집":
            return "중국음식"
        return None


def test_slot_normalizer_uses_fulltext_candidate_before_query_builder():
    normalizer = SlotNormalizer(FakeFallbackSearch())
    slot = ExtractedSlot("positive_condition", "Menu", "중국집", "", 0.4, False, True)

    normalized = normalizer.normalize(slot)

    assert normalized.normalized_value == "중국음식"
    assert normalized.confidence == 0.7
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `python -m pytest tests/test_slot_normalizer.py -v`

Expected: `ModuleNotFoundError`

- [ ] **Step 3: SlotNormalizer 구현**

`src/kag_graph/slot_normalizer.py`:

```python
from typing import Protocol

from kag_graph.models import ExtractedSlot


class FallbackSearch(Protocol):
    def find_candidate(self, node_label: str, raw_value: str) -> str | None:
        pass


class SlotNormalizationError(ValueError):
    pass


class SlotNormalizer:
    def __init__(self, fallback_search: FallbackSearch):
        self._fallback_search = fallback_search

    def normalize(self, slot: ExtractedSlot) -> ExtractedSlot:
        if slot.normalized_value:
            return slot

        candidate = self._fallback_search.find_candidate(slot.node_label, slot.raw_value)
        if candidate is None:
            raise SlotNormalizationError(slot.raw_value)

        return ExtractedSlot(
            slot_type=slot.slot_type,
            node_label=slot.node_label,
            raw_value=slot.raw_value,
            normalized_value=candidate,
            confidence=0.7,
            is_negative=slot.is_negative,
            is_required=slot.is_required,
        )
```

- [ ] **Step 4: 책임 경계 확인**

Run: `rg "fulltext|find_candidate" src/kag_graph/query_builder.py`

Expected: QueryBuilder에는 full-text fallback 호출이 없어야 한다.

- [ ] **Step 5: Commit**

```bash
git add src/kag_graph/slot_normalizer.py tests/test_slot_normalizer.py
git commit -m "feat: add slot normalization fallback boundary"
```

---

## Task 11: NLP Pipeline 통합

**Files:**
- Create: `src/kag_graph/nlp_pipeline.py`
- Test: `tests/test_nlp_pipeline.py`

- [ ] **Step 1: 자연어 전처리 통합 테스트 작성**

`tests/test_nlp_pipeline.py`:

```python
from kag_graph.constants import Domain, Intent
from kag_graph.domain_classifier import DomainClassifier
from kag_graph.intent_classifier import IntentClassifier
from kag_graph.nlp_pipeline import NLPPipeline
from kag_graph.slot_extractor import SlotExtractor
from kag_graph.slot_normalizer import SlotNormalizer
from kag_graph.slot_validator import SlotValidator


class NoFallbackSearch:
    def find_candidate(self, node_label: str, raw_value: str) -> str | None:
        return None


def test_nlp_pipeline_reaches_normalized_validated_slots():
    pipeline = NLPPipeline(
        DomainClassifier(),
        IntentClassifier(),
        SlotExtractor(),
        SlotValidator(),
        SlotNormalizer(NoFallbackSearch()),
    )

    result = pipeline.process("면은 싫은데 중국집 가고 싶어")

    assert result["status"] == "validated"
    assert result["domain"] == Domain.RESTAURANT
    assert result["intent"] == Intent.RESTAURANT_EXCLUSION_SEARCH
    assert len(result["slots"]) == 2


def test_nlp_pipeline_stops_ambiguous_text_as_clarification():
    pipeline = NLPPipeline(
        DomainClassifier(),
        IntentClassifier(),
        SlotExtractor(),
        SlotValidator(),
        SlotNormalizer(NoFallbackSearch()),
    )

    result = pipeline.process("요즘 뭐가 좋아?")

    assert result["status"] == "clarification_required"


class FakeLLMAssist:
    def suggest_domain(self, raw_text: str):
        from kag_graph.llm_assist import LLMAssistResult
        return LLMAssistResult(
            candidates=[{"domain": Domain.RESTAURANT, "confidence": 0.82}],
            confidence=0.82,
            reason="domain candidate",
            needs_clarification=False,
        )

    def suggest_intent(self, raw_text: str, domain: str):
        from kag_graph.llm_assist import LLMAssistResult
        return LLMAssistResult(
            candidates=[{"intent": Intent.RESTAURANT_EXCLUSION_SEARCH, "confidence": 0.86}],
            confidence=0.86,
            reason="intent candidate",
            needs_clarification=False,
        )

    def suggest_slots(self, raw_text: str, domain: str, intent: str):
        from kag_graph.llm_assist import LLMAssistResult
        return LLMAssistResult(candidates=[], confidence=0.0, reason="not used", needs_clarification=True)


class DomainNeedsAssist:
    def classify(self, raw_text: str):
        from kag_graph.constants import Domain
        from kag_graph.models import ClassificationResult
        return ClassificationResult(Domain.UNKNOWN, 0.4, "domain confidence too low", needs_llm_assist=True)


class IntentNeedsAssist:
    def classify(self, raw_text: str, domain: str):
        from kag_graph.constants import Intent
        from kag_graph.models import ClassificationResult
        return ClassificationResult(Intent.CLARIFICATION_REQUIRED, 0.4, "intent confidence too low", needs_llm_assist=True)


def test_nlp_pipeline_can_use_llm_assist_for_low_confidence_domain_and_intent():
    pipeline = NLPPipeline(
        DomainNeedsAssist(),
        IntentNeedsAssist(),
        SlotExtractor(),
        SlotValidator(),
        SlotNormalizer(NoFallbackSearch()),
        llm_assist=FakeLLMAssist(),
    )

    result = pipeline.process("면은 싫은데 중국집 가고 싶어")

    assert result["status"] == "validated"
    assert result["domain"] == Domain.RESTAURANT
    assert result["intent"] == Intent.RESTAURANT_EXCLUSION_SEARCH
```

- [ ] **Step 2: NLP Pipeline 구현**

`src/kag_graph/nlp_pipeline.py`:

```python
from kag_graph.models import ExtractedSlot


class NLPPipeline:
    def __init__(self, domain_classifier, intent_classifier, slot_extractor, slot_validator, slot_normalizer, llm_assist=None):
        self._domain_classifier = domain_classifier
        self._intent_classifier = intent_classifier
        self._slot_extractor = slot_extractor
        self._slot_validator = slot_validator
        self._slot_normalizer = slot_normalizer
        self._llm_assist = llm_assist

    def process(self, raw_text: str) -> dict[str, object]:
        domain_result = self._domain_classifier.classify(raw_text)
        if domain_result.needs_llm_assist:
            domain_result = self._domain_from_assist(raw_text, domain_result)

        if domain_result.value == "unknown":
            return {"status": "clarification_required", "message": domain_result.reason}

        intent_result = self._intent_classifier.classify(raw_text, domain_result.value)
        if intent_result.needs_llm_assist:
            intent_result = self._intent_from_assist(raw_text, domain_result.value, intent_result)

        if intent_result.value == "clarification_required":
            return {"status": "clarification_required", "message": intent_result.reason}

        slots = self._slot_extractor.extract(raw_text, domain_result.value, intent_result.value)
        if not slots and self._llm_assist is not None:
            assist_result = self._llm_assist.suggest_slots(raw_text, domain_result.value, intent_result.value)
            if assist_result.needs_clarification:
                return {"status": "clarification_required", "message": assist_result.reason}
            slots = self._slots_from_candidates(assist_result.candidates)

        normalized_slots = [self._slot_normalizer.normalize(slot) for slot in slots]
        validation = self._slot_validator.validate(intent_result.value, normalized_slots)
        if not validation.is_valid:
            return {"status": "clarification_required", "message": validation.message}

        return {
            "status": "validated",
            "domain": domain_result.value,
            "intent": intent_result.value,
            "slots": validation.slots,
        }

    def _slots_from_candidates(self, candidates: list[dict[str, object]]) -> list[ExtractedSlot]:
        return [
            ExtractedSlot(
                slot_type=str(candidate.get("slot_type", "positive_condition")),
                node_label=str(candidate["node_label"]),
                raw_value=str(candidate["raw_value"]),
                normalized_value=str(candidate.get("candidate_value", "")),
                confidence=float(candidate["confidence"]),
                is_negative=bool(candidate.get("is_negative", False)),
                is_required=True,
            )
            for candidate in candidates
        ]

    def _domain_from_assist(self, raw_text: str, fallback_result):
        if self._llm_assist is None:
            return fallback_result

        assist_result = self._llm_assist.suggest_domain(raw_text)
        if assist_result.needs_clarification or not assist_result.candidates:
            return fallback_result

        candidate = max(assist_result.candidates, key=lambda item: float(item["confidence"]))
        return type(fallback_result)(
            value=str(candidate["domain"]),
            confidence=float(candidate["confidence"]),
            reason=assist_result.reason,
            needs_llm_assist=False,
        )

    def _intent_from_assist(self, raw_text: str, domain: str, fallback_result):
        if self._llm_assist is None:
            return fallback_result

        assist_result = self._llm_assist.suggest_intent(raw_text, domain)
        if assist_result.needs_clarification or not assist_result.candidates:
            return fallback_result

        candidate = max(assist_result.candidates, key=lambda item: float(item["confidence"]))
        return type(fallback_result)(
            value=str(candidate["intent"]),
            confidence=float(candidate["confidence"]),
            reason=assist_result.reason,
            needs_llm_assist=False,
        )
```

- [ ] **Step 3: 테스트 실행**

Run: `python -m pytest tests/test_nlp_pipeline.py -v`

Expected: `3 passed`

- [ ] **Step 4: Commit**

```bash
git add src/kag_graph/nlp_pipeline.py tests/test_nlp_pipeline.py
git commit -m "feat: integrate rule first nlp pipeline"
```

---

## Task 12: Query Template 작성

**Files:**
- Create: `queries/restaurant/restaurant_menu_exclude_ingredient.cypher`
- Create: `queries/restaurant/restaurant_menu_required_tag_exclude_tag.cypher`
- Create: `queries/news/news_tech_event_search.cypher`
- Create: `queries/common/concept_bridge_search.cypher`

- [ ] **Step 1: 맛집 메뉴 + 재료 제외 Query 작성**

`queries/restaurant/restaurant_menu_exclude_ingredient.cypher`:

```cypher
MATCH (preferred:Menu {normalized_name: $menu_name})
MATCH (excluded:Ingredient {normalized_name: $excluded_ingredient})
MATCH path = (restaurant:Restaurant)-[:SELLS]->(menu:Menu)
WHERE restaurant.is_active = true
  AND (
    menu.normalized_name = preferred.normalized_name
    OR EXISTS {
      MATCH (menu)-[:RELATED_TO]->(preferred)
    }
  )
  AND NOT EXISTS {
    MATCH (menu)-[:CONTAINS]->(excluded)
  }
RETURN restaurant AS result_node,
       collect(path) AS evidence_paths,
       {
         prefers: preferred.normalized_name,
         excludes: excluded.normalized_name,
         exclude_type: "ingredient",
         exclude_strength: $exclude_strength
       } AS applied_conditions,
       coalesce(restaurant.rating, 0.0) AS score
ORDER BY restaurant.rating DESC
LIMIT $limit;
```

- [ ] **Step 2: 맛집 긍정 태그 + 부정 태그 Query 작성**

`queries/restaurant/restaurant_menu_required_tag_exclude_tag.cypher`:

```cypher
MATCH (menu:Menu {normalized_name: $menu_name})
MATCH (required:Tag {normalized_name: $required_tag})
MATCH (excluded:Tag {normalized_name: $excluded_tag})
MATCH path = (restaurant:Restaurant)-[:SELLS]->(menu)
MATCH tag_path = (restaurant)-[:HAS_TAG]->(required)
WHERE restaurant.is_active = true
  AND NOT EXISTS {
    MATCH (restaurant)-[:HAS_TAG]->(excluded)
  }
RETURN restaurant AS result_node,
       collect(path) + collect(tag_path) AS evidence_paths,
       {
         prefers: menu.normalized_name,
         requires: required.normalized_name,
         excludes: excluded.normalized_name,
         exclude_type: "tag",
         exclude_strength: $exclude_strength
       } AS applied_conditions,
       coalesce(restaurant.rating, 0.0) AS score
ORDER BY restaurant.rating DESC
LIMIT $limit;
```

- [ ] **Step 3: IT 뉴스 Technology + Event Query 작성**

`queries/news/news_tech_event_search.cypher`:

```cypher
MATCH (tech:Technology {normalized_name: $technology_name})
MATCH (event:Event {normalized_name: $event_name})
MATCH tech_path = (article:NewsArticle)-[:MENTIONS_TECH]->(tech)
MATCH event_path = (article)-[:DESCRIBES_EVENT]->(event)
RETURN article AS result_node,
       collect(tech_path) + collect(event_path) AS evidence_paths,
       {
         interested_in: tech.normalized_name,
         requests: event.normalized_name
       } AS applied_conditions,
       coalesce(article.importance_score, 0.0) AS score
ORDER BY article.published_at DESC
LIMIT $limit;
```

- [ ] **Step 4: Concept bridge Query 작성**

`queries/common/concept_bridge_search.cypher`:

```cypher
MATCH (concept:Concept {normalized_name: $concept_name})
CALL {
  WITH concept
  MATCH restaurant_path = (restaurant:Restaurant)-[:RELATED_TO]->(concept)
  RETURN restaurant AS result_node,
         collect(restaurant_path) AS evidence_paths,
         0.8 AS score
  UNION
  WITH concept
  MATCH article_path = (article:NewsArticle)-[:RELATED_TO]->(concept)
  RETURN article AS result_node,
         collect(article_path) AS evidence_paths,
         0.8 AS score
}
RETURN result_node,
       evidence_paths,
       {
         concept: concept.normalized_name,
         result_type: labels(result_node)[0]
       } AS applied_conditions,
       score;
```

- [ ] **Step 5: Commit**

```bash
git add queries/restaurant queries/news queries/common
git commit -m "feat: add graph query templates"
```

---

## Task 13: Query Repository 구현

**Files:**
- Create: `src/kag_graph/query_repository.py`
- Test: `tests/test_query_repository.py`

- [ ] **Step 1: 실패하는 템플릿 로딩 테스트 작성**

`tests/test_query_repository.py`:

```python
from pathlib import Path

from kag_graph.query_repository import QueryRepository


def test_query_repository_loads_template_by_name(tmp_path: Path):
    query_file = tmp_path / "sample.cypher"
    query_file.write_text("MATCH (n) RETURN n;", encoding="utf-8")

    repository = QueryRepository({"sample": query_file})

    assert repository.get("sample") == "MATCH (n) RETURN n;"
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `python -m pytest tests/test_query_repository.py -v`

Expected: `ModuleNotFoundError`

- [ ] **Step 3: Repository 구현**

`src/kag_graph/query_repository.py`:

```python
from pathlib import Path


class QueryTemplateNotFoundError(KeyError):
    pass


class QueryRepository:
    def __init__(self, template_paths: dict[str, Path]):
        self._template_paths = template_paths

    def get(self, template_name: str) -> str:
        path = self._template_paths.get(template_name)
        if path is None:
            raise QueryTemplateNotFoundError(template_name)

        return path.read_text(encoding="utf-8").strip()
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `python -m pytest tests/test_query_repository.py -v`

Expected: `1 passed`

- [ ] **Step 5: Commit**

```bash
git add src/kag_graph/query_repository.py tests/test_query_repository.py
git commit -m "feat: add query template repository"
```

---

## Task 14: GraphQueryBuilder 구현

**Files:**
- Modify: `src/kag_graph/query_builder.py`
- Modify: `tests/test_query_builder.py`

**MVP 지원 범위:**
- `TemplateName` 상수는 Design.md의 전체 Query Template 이름을 정의한다.
- 이 Task에서 실제 실행까지 지원하는 `_template_map`과 Param Builder는 1순위 테스트 대상인 `RESTAURANT_MENU_EXCLUDE_INGREDIENT`, `NEWS_TECH_EVENT_SEARCH` 두 개로 제한한다.
- `RESTAURANT_MENU_REQUIRED_TAG_EXCLUDE_TAG`와 `CONCEPT_BRIDGE_SEARCH`는 후속 확장 Task에서 Param Builder와 함께 `_template_map`에 등록한다.
- 나머지 템플릿은 해당 Query Template과 Param Builder가 함께 추가될 때 `_template_map`에 등록한다.

- [ ] **Step 1: 실패하는 QueryBuilder 테스트 추가**

`tests/test_query_builder.py`에 추가:

```python
from kag_graph.query_builder import GraphQueryBuilder


class FakeQueryRepository:
    def get(self, template_name: str) -> str:
        return f"-- {template_name}"


def test_query_builder_selects_restaurant_exclusion_template():
    slots = [
        ExtractedSlot("positive_condition", "Menu", "중국집", "중국음식", 0.95, False, True),
        ExtractedSlot("negative_condition", "Ingredient", "면", "면", 0.95, True, True),
    ]
    builder = GraphQueryBuilder(FakeQueryRepository())

    result = builder.build(
        query_id="Q001",
        domain=Domain.RESTAURANT,
        intent=Intent.RESTAURANT_EXCLUSION_SEARCH,
        slots=slots,
    )

    assert result.template_name == TemplateName.RESTAURANT_MENU_EXCLUDE_INGREDIENT
    assert result.params["menu_name"] == "중국음식"
    assert result.params["excluded_ingredient"] == "면"
    assert result.params["exclude_strength"] == "hard"
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `python -m pytest tests/test_query_builder.py -v`

Expected: `ModuleNotFoundError` 또는 `ImportError`

- [ ] **Step 3: QueryBuilder 구현**

`src/kag_graph/query_builder.py`:

```python
from kag_graph.constants import Domain, Intent, TemplateName
from kag_graph.models import ExtractedSlot, QueryBuildResult
from kag_graph.query_repository import QueryRepository


class UnsupportedQueryError(ValueError):
    pass


class MissingRequiredSlotError(ValueError):
    pass


class GraphQueryBuilder:
    def __init__(self, query_repository: QueryRepository):
        self._query_repository = query_repository
        self._template_map = {
            (Domain.RESTAURANT, Intent.RESTAURANT_EXCLUSION_SEARCH): TemplateName.RESTAURANT_MENU_EXCLUDE_INGREDIENT,
            (Domain.IT_NEWS, Intent.NEWS_EVENT_SEARCH): TemplateName.NEWS_TECH_EVENT_SEARCH,
        }

    def build(
        self,
        query_id: str,
        domain: str,
        intent: str,
        slots: list[ExtractedSlot],
    ) -> QueryBuildResult:
        template_name = self._select_template(domain, intent)
        params = self._build_params(query_id, template_name, slots)
        query_text = self._query_repository.get(template_name)

        return QueryBuildResult(
            template_name=template_name,
            query_text=query_text,
            params=params,
            expected_path_pattern=template_name,
        )

    def _select_template(self, domain: str, intent: str) -> str:
        template_name = self._template_map.get((domain, intent))
        if template_name is None:
            raise UnsupportedQueryError(f"{domain}:{intent}")

        return template_name

    def _build_params(
        self,
        query_id: str,
        template_name: str,
        slots: list[ExtractedSlot],
    ) -> dict[str, object]:
        if template_name == TemplateName.RESTAURANT_MENU_EXCLUDE_INGREDIENT:
            menu = self._required_slot(slots, "Menu", is_negative=False)
            ingredient = self._required_slot(slots, "Ingredient", is_negative=True)
            return {
                "query_id": query_id,
                "menu_name": menu.query_value,
                "excluded_ingredient": ingredient.query_value,
                "exclude_strength": "hard",
                "limit": 5,
            }

        if template_name == TemplateName.NEWS_TECH_EVENT_SEARCH:
            technology = self._required_slot(slots, "Technology", is_negative=False)
            event = self._required_slot(slots, "Event", is_negative=False)
            return {
                "query_id": query_id,
                "technology_name": technology.query_value,
                "event_name": event.query_value,
                "limit": 5,
            }

        raise UnsupportedQueryError(f"Parameter builder is not implemented for {template_name}")

    def _required_slot(
        self,
        slots: list[ExtractedSlot],
        node_label: str,
        is_negative: bool,
    ) -> ExtractedSlot:
        for slot in slots:
            if slot.node_label == node_label and slot.is_negative is is_negative:
                return slot

        raise MissingRequiredSlotError(node_label)
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `python -m pytest tests/test_query_builder.py -v`

Expected: 전체 통과

- [ ] **Step 5: Commit**

```bash
git add src/kag_graph/query_builder.py tests/test_query_builder.py
git commit -m "feat: map slots to graph query templates"
```

---

## Task 15: Clarification 흐름 추가

**Files:**
- Create: `src/kag_graph/pipeline.py`
- Test: `tests/test_pipeline.py`

- [ ] **Step 1: 필수 Slot 부족 시 Query를 실행하지 않는 테스트 작성**

`tests/test_pipeline.py`:

```python
from kag_graph.constants import Domain, Intent
from kag_graph.pipeline import QueryPipeline


class FailingBuilder:
    def build(self, query_id, domain, intent, slots):
        raise ValueError("missing required slot")


def test_pipeline_returns_clarification_without_query_execution():
    pipeline = QueryPipeline(FailingBuilder())

    result = pipeline.build_or_clarify(
        query_id="Q003",
        domain=Domain.RESTAURANT,
        intent=Intent.RESTAURANT_EXCLUSION_SEARCH,
        slots=[],
    )

    assert result["status"] == "clarification_required"
    assert result["query"] is None
```

- [ ] **Step 2: Pipeline 구현**

`src/kag_graph/pipeline.py`:

```python
from kag_graph.models import ExtractedSlot


class QueryPipeline:
    def __init__(self, query_builder):
        self._query_builder = query_builder

    def build_or_clarify(
        self,
        query_id: str,
        domain: str,
        intent: str,
        slots: list[ExtractedSlot],
    ) -> dict[str, object]:
        try:
            query = self._query_builder.build(query_id, domain, intent, slots)
            return {"status": "query_built", "query": query, "message": None}
        except ValueError as exc:
            return {
                "status": "clarification_required",
                "query": None,
                "message": str(exc),
            }
```

- [ ] **Step 3: 테스트 실행**

Run: `python -m pytest tests/test_pipeline.py -v`

Expected: `1 passed`

- [ ] **Step 4: Commit**

```bash
git add src/kag_graph/pipeline.py tests/test_pipeline.py
git commit -m "feat: stop ambiguous requests before graph search"
```

---

## Task 16: Neo4j Repository와 evidence path 반환

**Files:**
- Create: `src/kag_graph/neo4j_repository.py`
- Modify: `src/kag_graph/models.py`

- [ ] **Step 1: Neo4j Path DTO 변환 테스트 작성**

`tests/test_neo4j_repository.py`:

```python
from kag_graph.neo4j_repository import path_to_dto


def test_path_to_dto_keeps_nodes_and_relationships():
    path = None

    assert path_to_dto(path) is None
```

이 테스트는 실제 Neo4j `Path` 객체를 unit test에서 만들기 어렵기 때문에 boundary 함수의 빈 입력 처리만 확인한다. 실제 Path 변환은 integration test에서 검증한다.

- [ ] **Step 2: Neo4j 실행 래퍼 구현**

`src/kag_graph/neo4j_repository.py`:

```python
from neo4j import Driver

from kag_graph.models import EvidencePathDTO, GraphNodeDTO, GraphRelationshipDTO, GraphSearchResultDTO, QueryBuildResult


def node_to_dto(node) -> GraphNodeDTO:
    return GraphNodeDTO(labels=list(node.labels), properties=dict(node))


def relationship_to_dto(relationship, nodes_by_id: dict[int, GraphNodeDTO]) -> GraphRelationshipDTO:
    return GraphRelationshipDTO(
        type=relationship.type,
        start_node=nodes_by_id[relationship.start_node.id],
        end_node=nodes_by_id[relationship.end_node.id],
        properties=dict(relationship),
    )


def path_to_dto(path) -> EvidencePathDTO | None:
    if path is None:
        return None

    nodes = [node_to_dto(node) for node in path.nodes]
    nodes_by_id = {node.id: node_to_dto(node) for node in path.nodes}
    relationships = [
        relationship_to_dto(relationship, nodes_by_id)
        for relationship in path.relationships
    ]
    return EvidencePathDTO(nodes=nodes, relationships=relationships)


class Neo4jRepository:
    def __init__(self, driver: Driver, database: str):
        self._driver = driver
        self._database = database

    def run_query(self, query: QueryBuildResult) -> list[GraphSearchResultDTO]:
        with self._driver.session(database=self._database) as session:
            result = session.run(query.query_text, query.params)
            return [self._record_to_result(record) for record in result]

    def _record_to_result(self, record) -> GraphSearchResultDTO:
        evidence_paths = [
            path_dto
            for path_dto in (path_to_dto(path) for path in record["evidence_paths"])
            if path_dto is not None
        ]
        return GraphSearchResultDTO(
            result_node=node_to_dto(record["result_node"]),
            evidence_paths=evidence_paths,
            score=float(record["score"]),
        )
```

- [ ] **Step 3: 수동 검증 스크립트 대신 pytest integration marker 추가**

Neo4j가 로컬에서 실행 중일 때만 통합 테스트를 작성한다. Docker 또는 외부 Neo4j 준비 전에는 단위 테스트만 필수로 유지한다.

- [ ] **Step 4: Commit**

```bash
git add src/kag_graph/neo4j_repository.py tests/test_neo4j_repository.py
git commit -m "feat: add neo4j query repository"
```

---

## Task 17: 테스트 시나리오 구현

**Files:**
- Create: `tests/test_scenarios.py`

- [ ] **Step 1: 설계서 1순위 시나리오 테스트 작성**

`tests/test_scenarios.py`:

```python
from kag_graph.constants import Domain, Intent, TemplateName
from kag_graph.models import ExtractedSlot
from kag_graph.query_builder import GraphQueryBuilder


class FakeQueryRepository:
    def get(self, template_name: str) -> str:
        return f"-- {template_name}"


def test_r_03_menu_excludes_ingredient_template():
    builder = GraphQueryBuilder(FakeQueryRepository())
    slots = [
        ExtractedSlot("positive_condition", "Menu", "중국집", "중국음식", 0.95, False, True),
        ExtractedSlot("negative_condition", "Ingredient", "면", "면", 0.95, True, True),
    ]

    result = builder.build("Q001", Domain.RESTAURANT, Intent.RESTAURANT_EXCLUSION_SEARCH, slots)

    assert result.template_name == TemplateName.RESTAURANT_MENU_EXCLUDE_INGREDIENT
    assert result.params["menu_name"] == "중국음식"
    assert result.params["excluded_ingredient"] == "면"


def test_n_02_technology_event_template():
    builder = GraphQueryBuilder(FakeQueryRepository())
    slots = [
        ExtractedSlot("positive_condition", "Technology", "GPT", "gpt", 0.95, False, True),
        ExtractedSlot("event", "Event", "업데이트", "업데이트", 0.95, False, True),
    ]

    result = builder.build("Q002", Domain.IT_NEWS, Intent.NEWS_EVENT_SEARCH, slots)

    assert result.template_name == TemplateName.NEWS_TECH_EVENT_SEARCH
    assert result.params["technology_name"] == "gpt"
    assert result.params["event_name"] == "업데이트"
```

- [ ] **Step 2: 테스트 실행**

Run: `python -m pytest tests/test_scenarios.py -v`

Expected: `2 passed`

- [ ] **Step 3: 전체 테스트 실행**

Run: `python -m pytest -v`

Expected: 전체 통과

- [ ] **Step 4: Commit**

```bash
git add tests/test_scenarios.py
git commit -m "test: cover priority graph query scenarios"
```

---

## Task 18: LLM Path Interpreter 인터페이스 작성

**Files:**
- Create: `src/kag_graph/interpreter.py`
- Test: `tests/test_interpreter.py`

- [ ] **Step 1: 실패하는 interpreter 테스트 작성**

`tests/test_interpreter.py`:

```python
from kag_graph.interpreter import PathInterpreter


def test_interpreter_uses_only_evidence_paths():
    interpreter = PathInterpreter()
    answer = interpreter.explain(
        user_query="면은 싫은데 중국집 가고 싶어",
        evidence_paths=["Restaurant(홍콩반점)-[:SELLS]->Menu(중국음식)"],
    )

    assert "홍콩반점" in answer
    assert "근거" in answer
```

- [ ] **Step 2: 구현**

`src/kag_graph/interpreter.py`:

```python
class PathInterpreter:
    def explain(self, user_query: str, evidence_paths: list[str]) -> str:
        if not evidence_paths:
            return "근거 path가 없어 답변을 생성하지 않습니다. 추가 조건을 확인해야 합니다."

        evidence = "\n".join(f"- {path}" for path in evidence_paths)
        return f"요청: {user_query}\n근거:\n{evidence}"
```

- [ ] **Step 3: 테스트 실행**

Run: `python -m pytest tests/test_interpreter.py -v`

Expected: `1 passed`

- [ ] **Step 4: Commit**

```bash
git add src/kag_graph/interpreter.py tests/test_interpreter.py
git commit -m "feat: add path interpreter boundary"
```

---

## Task 19: 최종 검증

**Files:**
- Read: `docs/Design.md`
- Read: `docs/ImplementationPlan.md`

- [ ] **Step 1: 정적 구조 확인**

Run: `rg "Restaurant.*NewsArticle|NewsArticle.*Restaurant" queries src tests`

Expected: 직접 연결 Cypher가 없어야 한다. `concept_bridge_search.cypher`도 `result_node`, `evidence_paths`, `score` 공통 반환 포맷을 사용해야 한다.

- [ ] **Step 2: QueryBuilder 금지 규칙 확인**

Run: `rg "f\"|\\+ .*cypher|WHERE NOT .*LIKE|global " src queries tests`

Expected: Cypher f-string 조립, 문자열 기반 제외 필터, `global` 사용이 없어야 한다.

- [ ] **Step 3: 전체 테스트 실행**

Run: `python -m pytest -v`

Expected: 전체 통과

- [ ] **Step 4: Neo4j 수동 검증**

Run:

```bash
cypher-shell -u neo4j -p password "MATCH (r:Restaurant)-[:SELLS]->(m:Menu) RETURN r.name, m.name LIMIT 5;"
```

Expected: 맛집과 메뉴 관계가 반환된다.

Run:

```bash
cypher-shell -u neo4j -p password "MATCH (a:NewsArticle)-[:MENTIONS_TECH]->(t:Technology) RETURN a.title, t.name LIMIT 5;"
```

Expected: 뉴스와 기술 관계가 반환된다.

- [ ] **Step 5: Commit**

```bash
git status --short
git add docs/ImplementationPlan.md
git commit -m "docs: add kag graph implementation plan"
```

---

## 완료 기준

- DomainClassifier가 `restaurant`, `it_news`, `mixed`, `unknown`을 분류한다.
- IntentClassifier가 `constants.py`에 정의된 Intent 안에서만 intent를 선택한다.
- SlotExtractor가 자연어 발화에서 `ExtractedSlot` 목록을 만든다.
- LLM Assist는 후보만 제안하고 Cypher, Query Template, DB 결과를 생성하지 않는다.
- SlotValidator가 required slot 부족, 낮은 confidence, 허용되지 않은 node_label을 차단한다.
- NLP Pipeline이 정상 발화는 검증된 Slot까지 전달하고 애매한 발화는 `clarification_required`로 중단한다.
- Clarification 대상 발화는 QueryBuilder와 Neo4j Query를 실행하지 않는다.
- Neo4j 제약조건과 인덱스 Cypher가 존재한다.
- 맛집/IT 뉴스/Concept 공통 샘플 그래프 데이터가 존재한다.
- MVP QueryBuilder는 `RESTAURANT_MENU_EXCLUDE_INGREDIENT`, `NEWS_TECH_EVENT_SEARCH` 2개 템플릿을 실행 가능 상태로 지원한다.
- `RESTAURANT_MENU_REQUIRED_TAG_EXCLUDE_TAG`와 `CONCEPT_BRIDGE_SEARCH`는 후속 확장 Task에서 Param Builder와 함께 추가한다.
- QueryBuilder가 Intent/Slot을 템플릿명과 파라미터로 변환한다.
- 테스트가 `TEST-R-03`, `TEST-N-02` 우선 시나리오를 검증한다. `TEST-R-04`, `TEST-M-01`은 후속 확장 Task의 완료 기준으로 둔다.
- LLM Path Interpreter는 evidence path가 없으면 답변을 생성하지 않는다.
- `Restaurant`와 `NewsArticle`은 직접 연결되지 않는다.
