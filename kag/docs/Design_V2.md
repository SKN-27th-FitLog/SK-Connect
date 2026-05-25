# IT NEWS → KAG Keyword Extraction 통합 설계서

## 1. 설계 목적

본 설계는 IT 뉴스 기사 데이터를 기반으로:

```text
기사 → 형태소 분석 → 키워드 후보 추출 → 중요도 계산 → LLM 분류 → 검증 → JSONL 저장 → Neo4j 적재
```

까지의 전체 KAG Keyword Extraction 파이프라인을 정의한다.

핵심 원칙:

- Redis 사용 안 함
- 중간 저장은 JSONL/S3 기반
- Extraction과 Neo4j Import 분리
- LLM은 "추출"이 아니라 "분류"만 담당
- malformed article은 전체 파이프라인을 멈추지 않음
- PARTIAL_SUCCESS 허용
- 한국어 기사 기준 형태소 분석 우선 적용

---

# 2. 전체 아키텍처

```text
normalized_article.jsonl
↓
KoreanMorphAnalyzer
↓
TokenFilter
↓
CandidatePhraseBuilder
↓
ActionSignalExtractor
↓
CorpusContextBuilder
↓
HybridKeywordRanker
↓
DictionaryResolver
↓
LLM KeywordClassifier
↓
KeywordSchemaValidator
↓
KeywordExtractionWriter
↓
keyword_extraction.jsonl
↓
ItNewsImporter
↓
Neo4j
```

---

# 3. ExtractionService 설계

위치:

```text
kag/src/kag_graph/extraction/extraction_service.py
```

역할:

```text
normalized_article JSONL을 읽어서
keyword_extraction JSONL을 생성하는 orchestration 계층
```

책임:

- article read
- preprocessing 호출
- corpus 생성
- ranker 호출
- dictionary resolver 호출
- llm classifier 호출
- validator 호출
- writer 호출
- metrics 집계
- malformed article 처리

금지:

- Neo4j 직접 적재 금지
- S3 polling 금지
- Redis 저장 금지
- 직접 Cypher 생성 금지

---

# 4. 입력 스키마

입력 파일:

```text
normalized_article_*.jsonl
```

예시:

```json
{
  "schema_version": "news.article.v1",
  "article_id": "IT_20260512_GEEKNEWS_000001",
  "source": "geeknews",
  "category_cd": "IC02",
  "title": "기사 제목",
  "content": "기사 본문",
  "url": "https://example.com/article",
  "content_hash": "sha256_hash",
  "batch_id": "20260512_IC02_001",
  "run_attempt": 1
}
```

---

# 5. 출력 스키마

출력 파일:

```text
keyword_extraction_*.jsonl
```

예시:

```json
{
  "schema_version": "news.keyword_extraction.v3",
  "article_id": "IT_20260513_GEEKNEWS_000001",
  "source": "geeknews",
  "category_cd": "IC02",
  "title": "기사 제목",
  "url": "https://example.com/article",
  "published_at": "2026-05-13T09:00:00+09:00",
  "content_hash": "sha256_hash",
  "keywords": [
    {
      "canonical_name": "OpenAI",
      "matched_keyword": "ChatGPT",
      "node_type": "Company",
      "importance_score": 0.94,
      "classification_confidence": 1.0,
      "source": "dictionary"
    }
  ],
  "event_signals": [
    {
      "action_type": "RELEASE",
      "matched_text": "출시",
      "confidence": 0.8,
      "source": "morph_action_dictionary"
    }
  ],
  "keyword_count": 1,
  "ranking_method": "tfidf_textrank_hybrid_v1",
  "review_required": true,
  "review_reasons": [
    "LOW_KEYWORD_COUNT"
  ],
  "batch_id": "20260513_IC02_001",
  "run_attempt": 1,
  "created_at": "2026-05-13T21:30:12+09:00"
}
```

ranking_method는 추후 scoring 로직 변경 시 재현성과 replay 분석을 위해 저장한다.

---

# 6. KoreanPreprocessor 설계

위치:

```text
kag/src/kag_graph/extraction/preprocessing/
```

구성:

```text
korean_morph_analyzer.py
token_filter.py
candidate_phrase_builder.py
action_signal_extractor.py
```

## 형태소 분석기

선택:

```text
Kiwi
```

사용 품사:

```text
NNG
NNP
SL
SN
SH
VV 일부
```

VV는 중요 동사 allowlist만 사용.

---

# 7. CandidatePhraseBuilder

선택:

```text
방안 02.5
단일 token + 2~3gram phrase + action signal 보강
```

생성 규칙:

```text
NNG + NNG
NNP + NNP
SL + NNG
NNG + SL
SL + SN
```

예시:

```text
생성형 AI
대규모 언어 모델
AI 반도체
GPT-5
```

필터링 규칙:

- 1글자 제거
- 숫자-only 제거
- stopword 제거
- 너무 긴 phrase 제거
- 조사/어미 제거

설정:

```text
ngram_range = 1~3
max_phrase_length_chars = 40
```

---

# 8. ActionSignalExtractor

선택:

```text
event_signals optional field 저장
Neo4j 관계 생성은 2차 고도화
```

정책:

```text
중요 동사는 직접 Keyword node로 생성하지 않는다.
동사는 keyword가 아니라 event/action signal로 취급한다.
```

예:

```text
출시
공개
투자
해킹
```

1차 구현:

```text
NewsArticle.event_signals 속성으로만 보존
관계 생성은 수행하지 않음
```

예시 action_type:

```text
RELEASE
ANNOUNCEMENT
BUSINESS_DEAL
INVESTMENT
SECURITY_RISK
SERVICE_INCIDENT
POLICY_REGULATION
OPEN_SOURCE
RESEARCH
```

예시 mapping:

```json
{
  "RELEASE": ["출시", "배포", "릴리즈"],
  "ANNOUNCEMENT": ["공개", "발표"],
  "BUSINESS_DEAL": ["인수", "합병", "제휴"],
  "SECURITY_RISK": ["해킹", "유출", "취약점"]
}
```

---

# 9. CorpusContext 설계

선택:

```text
방안 02
batch 단위 corpus
```

의미:

```text
현재 normalized_article_*.jsonl 전체 기사
=
TF-IDF 비교 기준
```

구조:

```python
@dataclass
class CorpusContext:
    category_cd: str
    batch_id: str
    document_count: int
    documents: list[str]
    article_ids: list[str]
    corpus_version: str
```

small corpus 처리:

```text
min_corpus_document_count = 10

document_count < 10
→ review_required = true
→ review_reasons += SMALL_CORPUS_SIZE
```

---

# 10. HybridKeywordRanker

구성:

```text
TF-IDF
TextRank
TitleBoost
```

점수 공식:

```text
final_score =
  0.5 * tfidf_score
+ 0.3 * textrank_score
+ 0.2 * title_boost
```

정책:

```text
max_keywords_per_article = 10
min_importance_score = 0.15
```

규칙:

```text
10개 미만이면 가능한 만큼 저장
10개 초과면 상위 10개 사용
0~2개면 review_required
```

---

# 11. DictionaryResolver

목적:

```text
known keyword 보정
alias 통합
node_type 안정화
LLM 비용 감소
```

매칭 방식:

```text
Exact + Lowercase + Trim + Alias Match
```

사용하지 않는 것:

```text
fuzzy match
부분 문자열 match
유사도 match
```

예시:

```json
{
  "canonical_name": "OpenAI",
  "node_type": "Company",
  "aliases": ["openai", "OpenAI", "chatgpt 개발사"]
}
```

Dictionary Alias Conflict:

```text
동일 alias가 여러 canonical_name에 매칭될 경우:

- dictionary 확정 금지
- LLM classifier로 전달
- review_required = true
- review_reasons += DICTIONARY_ALIAS_CONFLICT
```

---

# 12. LLM Keyword Classifier

LLM 역할:

```text
keyword 추출 아님
node_type 분류만 수행
```

허용 node_type:

```text
Technology
Company
Event
Topic
Ignore
```

선택:

```text
article 단위 keyword 묶음 호출
```

context 정책:

```text
title + content 앞부분 일부
content_head_max_chars = 1500
```

LLM 실패 처리 정책:

```text
LLM classification 실패 시:

- dictionary 확정 keyword는 유지
- 미분류 keyword는 제외
- article 전체 FAIL로 즉시 처리하지 않음
- review_required = true
- review_reasons += LLM_CLASSIFICATION_FAILED
```

---

# 13. LLM Provider 구조

구성:

```text
llm_client.py
providers/
  ollama_client.py
  mock_llm_client.py
```

선택:

```text
config 기반 provider factory
```

설정:

```text
LLM_PROVIDER=ollama
LLM_MODEL=gemma
LLM_TIMEOUT_SECONDS=20
LLM_RETRY_COUNT=1
```

---

# 14. ResponseParser

선택:

```text
JSON block 추출 1회 시도 후 실패 시 article FAIL
```

처리 흐름:

```text
1차 JSON parse
↓
실패 시 JSON block 추출
↓
재parse
↓
실패 시 LLM_RESPONSE_PARSE_FAILED
```

---

# 15. KeywordSchemaValidator

책임:

- schema 검증
- Ignore 제거
- confidence threshold 적용
- dedup
- review_required 판정

confidence 기준:

```text
>= 0.75
→ 정상 채택

0.50 ~ 0.75
→ 채택 + review_required

< 0.50
→ 제외
```

Ignore 처리:

```text
Ignore는 extraction 실패를 의미하지 않는다.
graph node 가치가 낮은 keyword를 의미한다.

예:
- 일반 단어
- 불명확 표현
- 비IT 표현

최종 결과에서 제거
Neo4j 적재 금지
```

Validator 실패 처리 정책:

```text
복구 가능 오류:
- confidence 누락
- node_type = Ignore
- 허용되지 않는 node_type
- canonical_name 공백
- matched_keyword 공백
- confidence < 0.50

처리:
→ keyword 제외 또는 review_required 처리

복구 불가 오류:
- LLM 응답 전체 JSON parse 불가
- keywords가 list가 아님
- article_id 불일치

처리:
→ article FAIL
```

review_required 자동 조건:

```text
keyword_count < 3
→ LOW_KEYWORD_COUNT

document_count < 10
→ SMALL_CORPUS_SIZE

dictionary alias 충돌
→ DICTIONARY_ALIAS_CONFLICT

LLM 분류 실패
→ LLM_CLASSIFICATION_FAILED

Ignore 제거 후 keyword_count = 0
→ ALL_KEYWORDS_IGNORED

confidence 0.50 ~ 0.75 keyword 존재
→ LOW_CONFIDENCE_KEYWORD
```

review_reasons:

```text
list 구조
```

예시:

```json
{
  "review_required": true,
  "review_reasons": [
    "LOW_KEYWORD_COUNT",
    "LOW_CONFIDENCE_KEYWORD"
  ]
}
```

---

# 16. malformed article 처리

review_required와 malformed는 서로 다르다.

```text
review_required
= 정상 keyword_extraction 결과는 저장되지만
  사람 검토가 필요한 상태

malformed
= 정상 keyword_extraction record 생성 자체가 실패한 상태
```

선택:

```text
malformed_article.jsonl 별도 저장
```

경로:

```text
status=fail/
  malformed_article_{batch_id}_{timestamp}.jsonl
```

예시 reason_code:

```text
ARTICLE_SCHEMA_INVALID
EMPTY_TITLE
EMPTY_CONTENT
KEYWORD_RANKING_FAILED
LLM_CLASSIFICATION_FAILED
LLM_RESPONSE_PARSE_FAILED
VALIDATOR_FAILED
ARTICLE_ID_MISMATCH
NO_VALID_KEYWORDS
UNKNOWN_EXTRACTION_ERROR
```

---

# 17. Metrics 설계

선택:

```text
batch summary metrics JSON 저장
```

경로:

```text
status=metrics/
  keyword_extraction_metrics_{batch_id}_{timestamp}.json
```

metrics 예시:

```json
{
  "total_article_count": 100,
  "success_article_count": 91,
  "malformed_article_count": 6,
  "review_required_count": 18,
  "total_keyword_count": 642,
  "status": "PARTIAL_SUCCESS"
}
```

---

# 18. Writer 설계

위치:

```text
writer/keyword_extraction_writer.py
```

원칙:

```text
overwrite 금지
항상 새 파일 생성
UTF-8 고정
JSONL line write
```

overwrite 금지 이유:

```text
- run_attempt별 traceability 확보
- 재처리 이력 보존
- malformed/debug 분석 가능
- ingestion replay 가능
```

파일명:

```text
keyword_extraction_{batch_id}_{timestamp}.jsonl
```

---

# 19. Neo4j Import 설계

흐름:

```text
keyword_extraction.jsonl
↓
ItNewsIngestionHandler
↓
ItNewsImporter
↓
Neo4j
```

생성 Node:

```text
(:NewsArticle)
(:Technology)
(:Company)
(:Event)
(:Topic)
```

생성 Relationship:

```text
(NewsArticle)-[:MENTIONS_TECHNOLOGY]->(Technology)
(NewsArticle)-[:MENTIONS_COMPANY]->(Company)
(NewsArticle)-[:MENTIONS_EVENT]->(Event)
(NewsArticle)-[:HAS_TOPIC]->(Topic)
```

MERGE 기준:

```text
canonical_name
```

권장 Neo4j Constraint:

```cypher
CREATE CONSTRAINT technology_name_unique IF NOT EXISTS
FOR (n:Technology)
REQUIRE n.canonical_name IS UNIQUE;

CREATE CONSTRAINT company_name_unique IF NOT EXISTS
FOR (n:Company)
REQUIRE n.canonical_name IS UNIQUE;

CREATE CONSTRAINT event_name_unique IF NOT EXISTS
FOR (n:Event)
REQUIRE n.canonical_name IS UNIQUE;

CREATE CONSTRAINT topic_name_unique IF NOT EXISTS
FOR (n:Topic)
REQUIRE n.canonical_name IS UNIQUE;
```

event_signals 처리:

```text
NewsArticle.event_signals 속성에 JSON 형태 저장
관계 생성은 2차 고도화
```

---

# 20. 최종 구현 순서

```text
1. models.py
2. KoreanPreprocessor
3. CorpusContextBuilder
4. HybridKeywordRanker
5. DictionaryResolver
6. LLM Classifier
7. KeywordSchemaValidator
8. KeywordExtractionWriter
9. ExtractionService
10. ItNewsImporter
11. 테스트
```

---

# 21. 최종 핵심 원칙 요약

```text
- Redis 사용 안 함
- JSONL/S3 기반 중간 산출물 유지
- Extraction과 Import 분리
- 한국어 형태소 분석 우선
- 중요 동사는 event_signal로 분리
- LLM은 keyword 추출이 아니라 분류만 수행
- malformed article은 fail JSONL로 저장
- PARTIAL_SUCCESS 허용
- Neo4j 관계 생성은 2차 고도화
- batch 단위 corpus 기반 TF-IDF 사용
```
