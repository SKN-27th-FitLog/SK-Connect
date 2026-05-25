============================================================
[STEP 01] 그래프 DB 구현 범위 확정
============================================================

목표:
- 맛집 / IT 뉴스 도메인을 Neo4j 그래프 DB로 구현 가능한 구조로 변환한다.
- 단, 처음부터 모든 기능을 구현하지 않고 테스트 가능한 최소 그래프부터 만든다.
- 사용자 발화는 직접 DB에 저장하지 않고, Intent/Slot 추출 결과를 그래프 탐색 조건으로 사용한다.

============================================================
1. 현재 기준 파일에서 확정된 공통 흐름
============================================================

사용자 발화 처리 순서:

1) 원문 발화 입력
2) 도메인 분류
   - restaurant
   - it_news

3) Intent 분류
   - 맛집: 추천, 제외조건검색, 상황기반추천 등
   - IT 뉴스: 요약, 비교, 트렌드분석, 관점기반필터링 등

4) Slot 추출
   - 긍정 조건
   - 부정 조건
   - 상황 조건
   - 시간 조건
   - 비교 대상
   - 관심 주제

5) 그래프 탐색 조건 생성
6) Neo4j Cypher Query 실행
7) 결과 반환


============================================================
3. 최종 선택
============================================================

추천 선택:
- [방안 03: 맛집 / IT 뉴스 그래프 DB를 분리해서 동시에 설계]

이유:
- 업로드한 기준 파일 자체가 맛집과 IT 뉴스를 모두 대상으로 하고 있음
- 두 도메인의 노드/엣지 구조가 완전히 다르기 때문에 하나로 억지 통합하면 설계가 지저분해짐
- 하지만 공통 처리 흐름은 동일함
  - 원문 발화
  - 도메인 분류
  - Intent 분류
  - Slot 추출
  - 그래프 탐색 조건 생성

따라서 구조는 다음처럼 가져간다.

1) 공통 계층
   - UserQuery
   - UserIntent
   - Slot
   - Domain

2) 맛집 그래프 계층
   - Restaurant
   - Area
   - Tag
   - Menu
   - Ingredient

3) IT 뉴스 그래프 계층
   - NewsArticle
   - Topic
   - Company
   - Technology
   - Event
   - Audience

4) 실행 순서
   - STEP 01: 구현 범위 확정
   - STEP 02: 공통 그래프 처리 흐름 정의
   - STEP 03: 맛집 그래프 DB 스키마 확정
   - STEP 04: IT 뉴스 그래프 DB 스키마 확정
   - STEP 05: Neo4j 제약조건/인덱스 설계
   - STEP 06: 샘플 데이터 설계
   - STEP 07: Cypher 쿼리 패턴 설계
   - STEP 08: 사용자 발화 → Slot → Query 변환 설계
   - STEP 09: 테스트 시나리오별 검증 기준 작성
   - STEP 10: 최종 구현용 설계서 통합

============================================================
[STEP 01 결론]
============================================================

이번 그래프 DB 구현 설계는 다음 원칙으로 진행한다.

1. 맛집과 IT 뉴스는 같은 Neo4j DB 안에 둘 수 있지만, 도메인별 노드/엣지는 분리한다.

2. UserIntent는 공통 개념으로 사용한다.

3. Restaurant과 NewsArticle은 직접 연결하지 않는다.

4. 사용자 발화 원문은 그래프에 바로 넣지 않고, Intent/Slot으로 변환한 뒤 탐색 조건으로 사용한다.

5. 첫 구현 목표는 완성형 서비스가 아니라 테스트 가능한 KAG 그래프 구조다.

6. 공통 처리 흐름은 유지한다.
   - 원문 발화
   - 도메인 분류
   - Intent 분류
   - Slot 추출
   - 그래프 탐색 조건 생성
   - Cypher Query 실행
   - 결과 Path 반환
   - LLM Path 해석

7. Concept 또는 Tag 노드를 통해 도메인 간 느슨한 연결고리를 만든다.

8. Property 기반 검색보다 Relationship 기반 탐색을 우선한다.

9. LLM은 그래프 DB 결과를 임의 생성하지 않고, 반환된 Path를 해석하는 추론 레이어로 사용한다.
============================================================
[STEP 02] 공통 그래프 처리 흐름 정의
============================================================

목표:
- 맛집 / IT 뉴스 도메인에 공통으로 적용되는 KAG 처리 흐름을 확정한다.
- 사용자 발화를 바로 검색하지 않고, Intent/Slot/Graph Query/Path 해석 구조로 분리한다.

============================================================
1. 전체 처리 흐름
============================================================

사용자 발화
   ↓
[1] UserQuery 저장
   ↓
[2] DomainClassifier
   ↓
[3] IntentClassifier
   ↓
[4] SlotExtractor
   ↓
[5] GraphQueryBuilder
   ↓
[6] Neo4j Query 실행
   ↓
[7] Graph Path 반환
   ↓
[8] LLM Path Interpreter
   ↓
최종 응답 생성

============================================================
2. 단계별 역할
============================================================

[1] UserQuery 저장

역할:
- 사용자가 입력한 원문 발화를 보존한다.
- 원문은 직접 검색 조건으로 사용하지 않는다.

저장 예시:
- query_id: Q001
- raw_text: "면은 싫은데 중국집 가고 싶어"
- created_at: 2026-05-03T00:00:00
- domain: null
- intent: null

주의:
- raw_text는 기록용이다.
- 그래프 탐색은 raw_text가 아니라 추출된 Slot을 기준으로 한다.


------------------------------------------------------------
[2] DomainClassifier
------------------------------------------------------------

역할:
- 사용자 발화가 어떤 도메인인지 분류한다.

도메인:
- restaurant
- it_news
- unknown

예시:
- "강남에서 조용한 파스타집 추천해줘"
  → restaurant

- "최근 GPT 업데이트 알려줘"
  → it_news

- "요즘 뭐가 좋아?"
  → unknown 또는 clarification

주의:
- 도메인이 불명확하면 바로 검색하지 않는다.
- Clarification 대상으로 보낸다.


------------------------------------------------------------
[3] IntentClassifier
------------------------------------------------------------

역할:
- 사용자의 요청 목적을 분류한다.

맛집 Intent 예시:
- restaurant_recommendation
- restaurant_exclusion_search
- restaurant_context_recommendation
- restaurant_price_filter
- restaurant_area_search

IT 뉴스 Intent 예시:
- news_summary
- news_trend_analysis
- news_comparison
- news_event_search
- news_audience_filter

공통 Intent 예시:
- clarification_required
- unsupported_request

주의:
- Intent는 Query Template 선택에 사용된다.
- LLM 응답 스타일을 정하는 용도로만 쓰면 안 된다.


------------------------------------------------------------
[4] SlotExtractor
------------------------------------------------------------

역할:
- 발화에서 그래프 탐색에 필요한 조건을 추출한다.

공통 Slot 구조:

slot_type:
- positive_condition
- negative_condition
- context_condition
- time_condition
- comparison_target
- audience
- topic
- area
- menu
- ingredient
- company
- technology
- event

Slot 예시 01:
발화:
- "면은 싫은데 중국집 가고 싶어"

추출:
- domain: restaurant
- intent: restaurant_exclusion_search
- positive_condition:
  - Menu: 중국음식
- negative_condition:
  - Ingredient: 면


Slot 예시 02:
발화:
- "최근 GPT 관련 업데이트 알려줘"

추출:
- domain: it_news
- intent: news_event_search
- positive_condition:
  - Technology: GPT
- event:
  - 업데이트
- time_condition:
  - 최근

주의:
- Slot은 그래프 Query 생성의 직접 입력이다.
- 애매한 Slot은 확정값으로 만들지 않는다.
- 불명확한 조건은 clarification_required로 보낸다.


------------------------------------------------------------
[5] GraphQueryBuilder
------------------------------------------------------------

역할:
- Intent와 Slot을 Cypher Query Template으로 변환한다.

입력:
- domain
- intent
- slots

출력:
- cypher_query
- query_params
- expected_path_pattern

예시:
입력:
- domain: restaurant
- intent: restaurant_exclusion_search
- positive_condition: Menu(중국음식)
- negative_condition: Ingredient(면)

생성 Query 개념:
- 중국음식을 판매하는 Restaurant 탐색
- 면 Ingredient를 포함한 Menu는 제외
- Restaurant → SELLS → Menu
- Menu → CONTAINS → Ingredient 관계 사용

주의:
- QueryBuilder는 문자열을 무작위 조합하지 않는다.
- Intent별 Template 기반으로 생성한다.
- Property 검색보다 Relationship 탐색을 우선한다.


------------------------------------------------------------
[6] Neo4j Query 실행
------------------------------------------------------------

역할:
- GraphQueryBuilder가 만든 Cypher를 실행한다.

반환값:
- result_nodes
- result_relationships
- result_paths
- score
- evidence

주의:
- 결과는 단순 row가 아니라 Path 중심으로 반환한다.
- LLM이 해석할 수 있도록 근거 관계를 포함해야 한다.


------------------------------------------------------------
[7] Graph Path 반환
------------------------------------------------------------

역할:
- 검색 결과의 근거를 Path 형태로 구성한다.

맛집 Path 예시:
- UserIntent(Q001)
  -[:PREFERS]->
  Menu(중국음식)

- Restaurant(홍콩반점)
  -[:SELLS]->
  Menu(중국음식)

- UserIntent(Q001)
  -[:EXCLUDES]->
  Ingredient(면)

- Menu(짜장면)
  -[:CONTAINS]->
  Ingredient(면)

해석:
- 홍콩반점은 중국음식을 판매한다.
- 단, 짜장면은 면을 포함하므로 제외 대상이다.
- 면이 없는 메뉴 또는 식당 후보만 최종 추천한다.


IT 뉴스 Path 예시:
- UserIntent(Q002)
  -[:INTERESTED_IN]->
  Technology(GPT)

- UserIntent(Q002)
  -[:REQUESTS]->
  Event(업데이트)

- NewsArticle(A001)
  -[:MENTIONS_TECH]->
  Technology(GPT)

- NewsArticle(A001)
  -[:DESCRIBES_EVENT]->
  Event(업데이트)

해석:
- 해당 기사는 GPT를 언급한다.
- 기사 내용은 업데이트 이벤트와 연결되어 있다.
- 따라서 사용자 요청 조건과 일치한다.


------------------------------------------------------------
[8] LLM Path Interpreter
------------------------------------------------------------

역할:
- Neo4j에서 반환된 Path를 자연어로 설명한다.
- 없는 노드/관계를 임의로 만들지 않는다.
- 검색 결과를 조작하지 않는다.

입력:
- user_query
- extracted_slots
- graph_paths
- result_nodes

출력:
- 최종 답변
- 추천/요약 이유
- 제외된 조건 설명
- 추가 질문 필요 여부

주의:
- LLM은 추론 레이어다.
- LLM은 DB 역할을 대신하지 않는다.
- LLM은 계산/검색/조건판단의 최종 권한을 갖지 않는다.
- 모든 설명은 반환된 Path 기반이어야 한다.

============================================================
3. 공통 데이터 객체 설계
============================================================

[UserQuery]

필드:
- query_id
- raw_text
- domain
- intent
- created_at
- status

status:
- received
- classified
- slot_extracted
- query_built
- searched
- answered
- clarification_required
- failed


------------------------------------------------------------
[ExtractedSlot]

필드:
- slot_id
- query_id
- slot_type
- node_label
- value
- confidence
- is_negative
- is_required

예시:
- slot_type: positive_condition
- node_label: Menu
- value: 중국음식
- confidence: 0.92
- is_negative: false
- is_required: true


------------------------------------------------------------
[GraphSearchResult]

필드:
- result_id
- query_id
- domain
- result_node_id
- result_node_label
- path_summary
- score
- evidence_paths

예시:
- result_node_label: Restaurant
- result_node_id: R001
- path_summary: Restaurant-SELLS-Menu, Restaurant-HAS_TAG-Tag
- score: 0.87

============================================================
4. 공통 처리 원칙
============================================================

1. 사용자 발화는 직접 그래프 검색에 사용하지 않는다.

2. 발화는 반드시 Domain → Intent → Slot 순서로 구조화한다.

3. Slot이 부족하면 무리하게 검색하지 않고 Clarification으로 보낸다.

4. 그래프 검색은 Property보다 Relationship을 우선한다.

5. Neo4j 결과는 Node 목록만이 아니라 Path 중심으로 반환한다.

6. LLM은 반환된 Path를 해석한다.

7. LLM은 없는 관계를 생성하지 않는다.

8. Restaurant과 NewsArticle은 직접 연결하지 않는다.

9. 도메인 간 느슨한 연결은 Concept 또는 Tag 노드로 처리한다.

10. 구현 초기에는 테스트 가능한 최소 Query Template부터 만든다.

============================================================
5. 구현 순서 기준
============================================================

1순위:
- 공통 UserQuery / ExtractedSlot / GraphSearchResult 객체 정의

2순위:
- DomainClassifier 설계

3순위:
- IntentClassifier 설계

4순위:
- SlotExtractor 설계

5순위:
- GraphQueryBuilder 설계

6순위:
- Neo4j Query Template 설계

7순위:
- LLM Path Interpreter 설계

============================================================
[STEP 02 결론]
============================================================

공통 그래프 처리 흐름은 다음 구조로 확정한다.

UserQuery
→ DomainClassifier
→ IntentClassifier
→ SlotExtractor
→ GraphQueryBuilder
→ Neo4j Search
→ Graph Path Result
→ LLM Path Interpreter
→ Final Answer

============================================================
[STEP 03] 맛집 그래프 DB 스키마 확정
============================================================

목표:
- 맛집 도메인에서 Neo4j에 실제 구현 가능한 노드, 속성, 엣지를 확정한다.
- 추천, 제외조건검색, 상황기반추천, 가격조건검색을 처리할 수 있는 최소 그래프 구조를 만든다.

============================================================
1. 맛집 그래프 DB 설계 방향
============================================================

맛집 도메인은 다음 질문을 처리할 수 있어야 한다.

1) 지역 기반 추천
- "강남에서 분위기 좋은 이탈리안 추천해줘"

2) 메뉴/카테고리 기반 추천
- "초밥집 추천해줘"

3) 태그 기반 추천
- "조용한 카페 알려줘"

4) 부정 조건 검색
- "면은 싫은데 중국집 가고 싶어"

5) 재료 제외 검색
- "된장 들어간 음식은 싫고 한식 먹고 싶어"

6) 상황 기반 추천
- "회사 회식인데 6명 들어갈 수 있는 고기집 필요해"

7) 가격 조건 검색
- "혼자 가기 편한 한식집 중에 가격 1만원 이하로 알려줘"

============================================================
2. 노드 설계
============================================================

------------------------------------------------------------
[Restaurant]
------------------------------------------------------------

설명:
- 식당 자체를 의미하는 핵심 결과 노드

주요 속성:
- restaurant_id: 고유 ID
- name: 식당명
- address: 주소
- phone: 전화번호
- url: 상세 URL
- rating: 평점
- review_count: 리뷰 수
- min_price: 최소 가격
- max_price: 최대 가격
- avg_price: 평균 가격
- latitude: 위도
- longitude: 경도
- is_active: 사용 여부
- created_at: 생성일
- updated_at: 수정일

필수 속성:
- restaurant_id
- name

검색 결과로 반환 여부:
- 반환함

주의:
- area, menu, tag를 Restaurant 속성으로 직접 넣는 것을 최소화한다.
- 지역/메뉴/태그는 관계로 탐색한다.


------------------------------------------------------------
[Area]
------------------------------------------------------------

설명:
- 식당이 위치한 지역

주요 속성:
- area_id
- name
- parent_area
- level

예시:
- 강남
- 홍대
- 을지로
- 판교

검색 결과로 반환 여부:
- 보조 반환

주의:
- Area는 Restaurant과 LOCATED_IN 관계로 연결한다.
- "판교"처럼 IT 뉴스와도 연결될 수 있는 지역은 Concept 노드와도 연결 가능하다.


------------------------------------------------------------
[Menu]
------------------------------------------------------------

설명:
- 식당이 판매하는 메뉴 또는 음식 카테고리

주요 속성:
- menu_id
- name
- menu_type
- price
- normalized_name

menu_type 예시:
- category
- dish
- drink
- set_menu

예시:
- 한식
- 중국음식
- 이탈리안
- 초밥
- 파스타
- 닭발
- 와인바
- 카페
- 고기

검색 결과로 반환 여부:
- 보조 반환

주의:
- "중국집" 같은 표현은 Menu 또는 Category 개념으로 정규화한다.
- 초기 구현에서는 Menu 노드를 음식 카테고리와 개별 메뉴를 모두 담는 구조로 사용한다.


------------------------------------------------------------
[Ingredient]
------------------------------------------------------------

설명:
- 메뉴에 포함될 수 있는 재료 또는 음식 성분

주요 속성:
- ingredient_id
- name
- normalized_name

예시:
- 면
- 된장
- 고기
- 기름진음식

검색 결과로 반환 여부:
- 보조 반환

주의:
- 부정 조건 검색에서 중요하다.
- Menu -[:CONTAINS]-> Ingredient 관계로 연결한다.


------------------------------------------------------------
[Tag]
------------------------------------------------------------

설명:
- 식당의 분위기, 상황, 특성, 운영 조건을 표현하는 노드

주요 속성:
- tag_id
- name
- tag_type
- normalized_name

tag_type 예시:
- mood
- situation
- service
- taste
- operation
- negative_signal
- price_signal

예시:
- 조용한
- 분위기좋은
- 가성비
- 혼밥가능
- 데이트
- 회식
- 매운맛
- 담백한
- 배달가능
- 야간영업
- 깔끔한
- 어른동반적합
- 웨이팅긴
- 시끄러운
- 기름진음식

검색 결과로 반환 여부:
- 보조 반환

주의:
- Tag는 맛집 도메인의 핵심 탐색 축이다.
- 단, 너무 많은 의미를 Tag 하나에 몰아넣지 않도록 tag_type으로 구분한다.


------------------------------------------------------------
[PriceCondition]
------------------------------------------------------------

설명:
- 사용자 요청의 가격 조건을 표현하는 노드

주요 속성:
- condition_id
- operator
- value
- currency

예시:
- 10000 이하
- 20000 이하
- 30000 이하

검색 결과로 반환 여부:
- 일반적으로 반환하지 않음

주의:
- PriceCondition은 UserIntent와 연결된다.
- Restaurant의 avg_price 또는 Menu.price와 비교하는 데 사용한다.
- Neo4j에서는 가격 자체는 Property 비교가 필요하므로 예외적으로 Property 조건을 사용한다.


------------------------------------------------------------
[CapacityCondition]
------------------------------------------------------------

설명:
- 인원 수 조건을 표현하는 노드

주요 속성:
- condition_id
- min_capacity
- max_capacity

예시:
- 6명 가능
- 단체 가능

검색 결과로 반환 여부:
- 일반적으로 반환하지 않음

주의:
- 회식, 모임 조건에서 사용한다.
- Restaurant.max_capacity 속성과 함께 검증한다.


------------------------------------------------------------
[Context]
------------------------------------------------------------

설명:
- 사용자 상황 조건을 표현하는 노드

주요 속성:
- context_id
- name
- context_type

예시:
- 비
- 운동후
- 부모님동반
- 회사회식

검색 결과로 반환 여부:
- 보조 반환

주의:
- Context는 UserIntent와 연결한다.
- Restaurant은 보통 Context와 직접 연결하지 않고, Context에 적합한 Tag와 연결하는 구조를 우선한다.


------------------------------------------------------------
[Concept]
------------------------------------------------------------

설명:
- 맛집과 IT 뉴스 도메인을 느슨하게 연결하기 위한 공통 의미 노드

주요 속성:
- concept_id
- name
- concept_type

예시:
- 판교
- AI
- 스타트업
- 개발자

검색 결과로 반환 여부:
- 보조 반환

주의:
- Restaurant과 NewsArticle을 직접 연결하지 않는다.
- 필요한 경우 Restaurant -[:RELATED_TO]-> Concept 형태로 연결한다.
- 예:
  - Restaurant(판교파스타) -[:RELATED_TO]-> Concept(판교)
  - NewsArticle(판교 IT 기업 투자 뉴스) -[:RELATED_TO]-> Concept(판교)

============================================================
3. 엣지 설계
============================================================

------------------------------------------------------------
Restaurant -[:LOCATED_IN]-> Area
------------------------------------------------------------

설명:
- 식당이 특정 지역에 위치함

예:
- Restaurant(강남파스타) -[:LOCATED_IN]-> Area(강남)

사용 시나리오:
- "강남에서"
- "홍대 근처"
- "을지로 맛집"

필수 여부:
- 강력 권장


------------------------------------------------------------
Restaurant -[:HAS_TAG]-> Tag
------------------------------------------------------------

설명:
- 식당이 특정 특성을 가짐

예:
- Restaurant(조용한카페) -[:HAS_TAG]-> Tag(조용한)

사용 시나리오:
- 조용한
- 분위기좋은
- 혼밥가능
- 회식
- 배달가능
- 야간영업

필수 여부:
- 강력 권장


------------------------------------------------------------
Restaurant -[:SELLS]-> Menu
------------------------------------------------------------

설명:
- 식당이 특정 메뉴 또는 음식 카테고리를 판매함

예:
- Restaurant(홍대초밥) -[:SELLS]-> Menu(초밥)

사용 시나리오:
- 초밥집
- 한식
- 중국음식
- 파스타
- 고기집

필수 여부:
- 강력 권장


------------------------------------------------------------
Menu -[:CONTAINS]-> Ingredient
------------------------------------------------------------

설명:
- 메뉴가 특정 재료 또는 성분을 포함함

예:
- Menu(짜장면) -[:CONTAINS]-> Ingredient(면)

사용 시나리오:
- "면은 싫은데"
- "된장 들어간 음식은 싫고"
- "기름진 음식 말고"

필수 여부:
- 부정 조건 검색을 위해 필요


------------------------------------------------------------
UserIntent -[:TARGET_AREA]-> Area
------------------------------------------------------------

설명:
- 사용자 요청이 특정 지역을 대상으로 함

예:
- UserIntent(Q001) -[:TARGET_AREA]-> Area(강남)

사용 시나리오:
- "강남에서"
- "홍대 근처"

필수 여부:
- 발화에 지역이 있을 때만 생성


------------------------------------------------------------
UserIntent -[:PREFERS]-> Menu
------------------------------------------------------------

설명:
- 사용자 요청이 특정 메뉴/카테고리를 선호함

예:
- UserIntent(Q001) -[:PREFERS]-> Menu(중국음식)

사용 시나리오:
- "중국집 가고 싶어"
- "한식 먹고 싶어"
- "초밥집"

필수 여부:
- 발화에 음식/메뉴 조건이 있을 때 생성


------------------------------------------------------------
UserIntent -[:REQUIRES]-> Tag
------------------------------------------------------------

설명:
- 사용자 요청이 특정 태그 조건을 요구함

예:
- UserIntent(Q001) -[:REQUIRES]-> Tag(조용한)

사용 시나리오:
- "조용한"
- "혼밥 가능"
- "배달 가능한"
- "데이트하기 좋은"

필수 여부:
- 발화에 태그 조건이 있을 때 생성


------------------------------------------------------------
UserIntent -[:EXCLUDES]-> Menu / Ingredient / Tag
------------------------------------------------------------

설명:
- 사용자 요청에서 제외해야 하는 조건

예:
- UserIntent(Q001) -[:EXCLUDES]-> Ingredient(면)
- UserIntent(Q002) -[:EXCLUDES]-> Tag(시끄러운)

사용 시나리오:
- "면은 싫은데"
- "된장 들어간 음식은 싫고"
- "시끄러운 곳 말고"
- "웨이팅 긴 곳 제외"

필수 여부:
- 부정 조건 처리에서 필수


------------------------------------------------------------
UserIntent -[:MAX_PRICE]-> PriceCondition
------------------------------------------------------------

설명:
- 사용자 요청의 최대 가격 조건

예:
- UserIntent(Q001) -[:MAX_PRICE]-> PriceCondition(10000 이하)

사용 시나리오:
- "1만원 이하"
- "2만원 안쪽"

필수 여부:
- 가격 조건이 있을 때만 생성


------------------------------------------------------------
UserIntent -[:MIN_CAPACITY]-> CapacityCondition
------------------------------------------------------------

설명:
- 사용자 요청의 최소 수용 인원 조건

예:
- UserIntent(Q001) -[:MIN_CAPACITY]-> CapacityCondition(6명)

사용 시나리오:
- "6명 들어갈 수 있는"
- "단체 가능한"

필수 여부:
- 인원 조건이 있을 때만 생성


------------------------------------------------------------
UserIntent -[:HAS_CONTEXT]-> Context
------------------------------------------------------------

설명:
- 사용자 요청의 상황 조건

예:
- UserIntent(Q001) -[:HAS_CONTEXT]-> Context(운동후)

사용 시나리오:
- "비 오는데"
- "운동 끝나고"
- "부모님 모시고"

필수 여부:
- 상황 조건이 있을 때만 생성


------------------------------------------------------------
Restaurant -[:RELATED_TO]-> Concept
------------------------------------------------------------

설명:
- 도메인 간 느슨한 연결을 위한 공통 의미 연결

예:
- Restaurant(판교파스타) -[:RELATED_TO]-> Concept(판교)

사용 시나리오:
- "판교 맛집과 판교 IT 뉴스 같이 보고 싶어"

필수 여부:
- 초기 구현에서는 선택
- 확장 구조에서는 권장

============================================================
4. 맛집 도메인 최소 구현 스키마
============================================================

초기 구현에 반드시 필요한 노드:

1. Restaurant
2. Area
3. Menu
4. Ingredient
5. Tag
6. UserIntent

초기 구현에 선택적으로 추가할 노드:

1. PriceCondition
2. CapacityCondition
3. Context
4. Concept

초기 구현에 반드시 필요한 엣지:

1. Restaurant -[:LOCATED_IN]-> Area
2. Restaurant -[:HAS_TAG]-> Tag
3. Restaurant -[:SELLS]-> Menu
4. Menu -[:CONTAINS]-> Ingredient
5. UserIntent -[:TARGET_AREA]-> Area
6. UserIntent -[:PREFERS]-> Menu
7. UserIntent -[:REQUIRES]-> Tag
8. UserIntent -[:EXCLUDES]-> Menu / Ingredient / Tag

초기 구현에 선택적으로 추가할 엣지:

1. UserIntent -[:MAX_PRICE]-> PriceCondition
2. UserIntent -[:MIN_CAPACITY]-> CapacityCondition
3. UserIntent -[:HAS_CONTEXT]-> Context
4. Restaurant -[:RELATED_TO]-> Concept

============================================================
5. 맛집 그래프 탐색 기본 패턴
============================================================

------------------------------------------------------------
[패턴 01: 지역 + 메뉴 + 태그 추천]
------------------------------------------------------------

예시 발화:
- "강남에서 분위기 좋은 이탈리안 레스토랑 추천해줘"

탐색 조건:
- Restaurant -[:LOCATED_IN]-> Area(강남)
- Restaurant -[:SELLS]-> Menu(이탈리안)
- Restaurant -[:HAS_TAG]-> Tag(분위기좋은)

반환:
- Restaurant
- 연결된 Area
- 연결된 Menu
- 연결된 Tag
- 근거 Path


------------------------------------------------------------
[패턴 02: 메뉴 + 부정 재료 제외]
------------------------------------------------------------

예시 발화:
- "면은 싫은데 중국집 가고 싶어"

탐색 조건:
- Restaurant -[:SELLS]-> Menu(중국음식)
- 제외:
  - Menu -[:CONTAINS]-> Ingredient(면)

반환:
- 면이 포함되지 않은 메뉴/식당 후보
- 제외 근거


------------------------------------------------------------
[패턴 03: 태그 긍정 + 태그 부정]
------------------------------------------------------------

예시 발화:
- "시끄러운 곳 말고 조용한 카페 알려줘"

탐색 조건:
- Restaurant -[:SELLS]-> Menu(카페)
- Restaurant -[:HAS_TAG]-> Tag(조용한)
- 제외:
  - Restaurant -[:HAS_TAG]-> Tag(시끄러운)

반환:
- 조용한 카페
- 시끄러운 태그가 없는 식당


------------------------------------------------------------
[패턴 04: 상황 기반 추천]
------------------------------------------------------------

예시 발화:
- "부모님 모시고 갈 수 있는 깔끔한 식당 알려줘"

탐색 조건:
- UserIntent -[:HAS_CONTEXT]-> Context(부모님동반)
- UserIntent -[:REQUIRES]-> Tag(깔끔한)
- UserIntent -[:REQUIRES]-> Tag(어른동반적합)
- Restaurant -[:HAS_TAG]-> Tag(깔끔한)
- Restaurant -[:HAS_TAG]-> Tag(어른동반적합)

반환:
- 조건을 만족하는 Restaurant
- Context와 Tag 연결 근거


------------------------------------------------------------
[패턴 05: 가격 조건 검색]
------------------------------------------------------------

예시 발화:
- "혼자 가기 편한 한식집 중에 가격 1만원 이하로 알려줘"

탐색 조건:
- Restaurant -[:SELLS]-> Menu(한식)
- Restaurant -[:HAS_TAG]-> Tag(혼밥가능)
- Restaurant.avg_price <= 10000 또는 Menu.price <= 10000

주의:
- 가격은 관계 탐색만으로 처리하기 어렵다.
- 따라서 Property 조건을 보조적으로 사용한다.

============================================================
6. 설계상 중요한 결정
============================================================

1. Restaurant은 결과 중심 노드다.

2. Area, Menu, Tag, Ingredient는 탐색 조건 노드다.

3. 부정 조건은 반드시 UserIntent -[:EXCLUDES]-> 대상 노드로 표현한다.

4. "면", "된장", "기름진음식"처럼 제외될 수 있는 것은 Ingredient 또는 Tag로 분류한다.

5. 가격과 수용 인원은 Relationship만으로 처리하지 않고 Property 조건을 병행한다.

6. 맛집과 IT 뉴스를 직접 연결하지 않는다.

7. 도메인 간 연결이 필요하면 Concept 노드를 사용한다.

8. LLM은 검색 결과를 만들지 않고, 반환된 Path를 설명한다.

============================================================
[STEP 03 결론]
============================================================

맛집 그래프 DB는 다음 구조로 확정한다.

핵심 결과 노드:
- Restaurant

핵심 조건 노드:
- Area
- Menu
- Ingredient
- Tag

공통 요청 노드:
- UserIntent

확장 노드:
- PriceCondition
- CapacityCondition
- Context
- Concept

핵심 탐색 관계:
- Restaurant -[:LOCATED_IN]-> Area
- Restaurant -[:SELLS]-> Menu
- Restaurant -[:HAS_TAG]-> Tag
- Menu -[:CONTAINS]-> Ingredient
- UserIntent -[:TARGET_AREA]-> Area
- UserIntent -[:PREFERS]-> Menu
- UserIntent -[:REQUIRES]-> Tag
- UserIntent -[:EXCLUDES]-> Menu / Ingredient / Tag

============================================================
[STEP 04] IT 뉴스 그래프 DB 스키마 확정
============================================================

목표:
- IT 뉴스 도메인에서 Neo4j에 실제 구현 가능한 노드, 속성, 엣지를 확정한다.
- 요약, 트렌드 분석, 비교, 이벤트 탐색, 관점 기반 필터링을 처리할 수 있는 최소 그래프 구조를 만든다.

============================================================
1. IT 뉴스 그래프 DB 설계 방향
============================================================

IT 뉴스 도메인은 다음 질문을 처리할 수 있어야 한다.

1) 주제 기반 뉴스 탐색
- "요즘 AI 관련해서 중요한 뉴스 뭐 있어?"

2) 기술 업데이트 탐색
- "최근 GPT 관련 업데이트 알려줘"

3) 시장/산업 트렌드 분석
- "클라우드 시장에서 요즘 트렌드 뭐야?"

4) 기업 비교
- "삼성과 애플 최근 기술 경쟁 상황 어때?"

5) 이벤트 기반 탐색
- "생성형 AI 규제 관련해서 어떤 움직임 있어?"

6) 관점 기반 필터링
- "개발자 입장에서 중요한 IT 뉴스만 골라줘"

============================================================
2. 노드 설계
============================================================

------------------------------------------------------------
[NewsArticle]
------------------------------------------------------------

설명:
- 뉴스 기사 자체를 의미하는 핵심 결과 노드

주요 속성:
- article_id
- title
- content
- summary
- published_at
- url
- source
- author
- language
- importance_score
- reliability_score
- created_at
- updated_at

필수 속성:
- article_id
- title
- url
- published_at

검색 결과로 반환 여부:
- 반환함

주의:
- Topic, Company, Technology, Event를 NewsArticle 속성에 몰아넣지 않는다.
- 기사 본문은 RAG 검색용 원문으로도 사용할 수 있으나, 그래프 탐색은 관계 중심으로 수행한다.


------------------------------------------------------------
[Topic]
------------------------------------------------------------

설명:
- 뉴스가 다루는 상위 기술/산업 주제

주요 속성:
- topic_id
- name
- normalized_name
- topic_type

topic_type 예시:
- technology_area
- industry
- market
- policy
- security
- startup

예시:
- AI
- 클라우드
- 반도체
- 보안
- 데이터엔지니어링
- 스타트업
- 머신러닝
- IT

검색 결과로 반환 여부:
- 보조 반환

주의:
- Topic은 넓은 범위의 분류다.
- GPT, LLM, GPU처럼 구체 기술은 Technology 노드로 분리한다.


------------------------------------------------------------
[Technology]
------------------------------------------------------------

설명:
- 뉴스에 등장하는 구체 기술, 제품군, 기술 개념

주요 속성:
- technology_id
- name
- normalized_name
- technology_type

technology_type 예시:
- ai_model
- framework
- hardware
- platform
- software
- methodology
- open_source
- commercial_product

예시:
- GPT
- 생성형AI
- LLM
- GPU
- 자율주행
- 오픈소스AI
- 상용AI

검색 결과로 반환 여부:
- 보조 반환

주의:
- 기술명은 동의어 정규화가 필요하다.
- 예:
  - GPT-4, ChatGPT, OpenAI GPT → GPT 또는 GPT 계열로 정규화 가능


------------------------------------------------------------
[Company]
------------------------------------------------------------

설명:
- 뉴스에 등장하는 기업 또는 조직

주요 속성:
- company_id
- name
- normalized_name
- company_type
- country

company_type 예시:
- bigtech
- startup
- semiconductor
- cloud_provider
- ai_company
- automotive
- public_institution

예시:
- 삼성
- 애플
- 테슬라
- OpenAI
- Google
- Microsoft

검색 결과로 반환 여부:
- 보조 반환

주의:
- "빅테크"는 CompanyGroup 또는 Concept으로 처리할 수 있다.
- 초기 구현에서는 Company.company_type = bigtech 속성으로 처리하고, 확장 시 CompanyGroup 노드 분리를 고려한다.


------------------------------------------------------------
[Event]
------------------------------------------------------------

설명:
- 뉴스에서 설명하는 사건, 변화, 이슈 유형

주요 속성:
- event_id
- name
- normalized_name
- event_type

event_type 예시:
- update
- investment
- regulation
- security_incident
- product_launch
- trend
- competition
- issue
- decline
- comparison

예시:
- 업데이트
- 투자
- 규제
- 보안사고
- 제품출시
- 트렌드
- 기술경쟁
- 이슈
- 투자감소
- 비교분석

검색 결과로 반환 여부:
- 보조 반환

주의:
- Event는 기사에서 발생한 일을 표현한다.
- 단순 키워드가 아니라 "기사의 사건 유형"으로 관리한다.


------------------------------------------------------------
[Audience]
------------------------------------------------------------

설명:
- 사용자의 관점 또는 독자 유형

주요 속성:
- audience_id
- name
- normalized_name
- audience_type

예시:
- 개발자
- 창업자
- 데이터엔지니어
- 기획자
- 투자자

검색 결과로 반환 여부:
- 보조 반환

주의:
- Audience는 UserIntent와 연결된다.
- NewsArticle과 직접 연결할 수도 있지만, 초기에는 Topic/Event/Technology 기반 필터링을 우선한다.


------------------------------------------------------------
[Concept]
------------------------------------------------------------

설명:
- 맛집과 IT 뉴스 도메인을 느슨하게 연결하기 위한 공통 의미 노드

주요 속성:
- concept_id
- name
- concept_type
- normalized_name

예시:
- 판교
- AI
- 스타트업
- 개발자
- 클라우드

검색 결과로 반환 여부:
- 보조 반환

주의:
- Restaurant과 NewsArticle을 직접 연결하지 않는다.
- 필요한 경우 NewsArticle -[:RELATED_TO]-> Concept 형태로 연결한다.
- 예:
  - NewsArticle(판교 IT 기업 투자 뉴스) -[:RELATED_TO]-> Concept(판교)
  - Restaurant(판교파스타) -[:RELATED_TO]-> Concept(판교)

============================================================
3. 엣지 설계
============================================================

------------------------------------------------------------
NewsArticle -[:MENTIONS]-> Topic
------------------------------------------------------------

설명:
- 뉴스 기사가 특정 상위 주제를 언급함

예:
- NewsArticle(A001) -[:MENTIONS]-> Topic(AI)

사용 시나리오:
- "AI 관련 뉴스"
- "보안 관련 사고"
- "반도체 업계 상황"

필수 여부:
- 강력 권장


------------------------------------------------------------
NewsArticle -[:MENTIONS_TECH]-> Technology
------------------------------------------------------------

설명:
- 뉴스 기사가 구체 기술을 언급함

예:
- NewsArticle(A001) -[:MENTIONS_TECH]-> Technology(GPT)

사용 시나리오:
- "GPT 관련 업데이트"
- "생성형 AI 규제"
- "자율주행 이슈"

필수 여부:
- 강력 권장


------------------------------------------------------------
NewsArticle -[:MENTIONS_COMPANY]-> Company
------------------------------------------------------------

설명:
- 뉴스 기사가 특정 기업을 언급함

예:
- NewsArticle(A001) -[:MENTIONS_COMPANY]-> Company(OpenAI)

사용 시나리오:
- "삼성과 애플"
- "테슬라 자율주행"
- "빅테크 투자 흐름"

필수 여부:
- 강력 권장


------------------------------------------------------------
NewsArticle -[:DESCRIBES_EVENT]-> Event
------------------------------------------------------------

설명:
- 뉴스 기사가 특정 사건 유형을 설명함

예:
- NewsArticle(A001) -[:DESCRIBES_EVENT]-> Event(업데이트)

사용 시나리오:
- 업데이트
- 투자
- 규제
- 보안사고
- 제품출시
- 트렌드
- 기술경쟁

필수 여부:
- 강력 권장


------------------------------------------------------------
Company -[:RELATED_TO]-> Technology
------------------------------------------------------------

설명:
- 기업이 특정 기술과 관련됨

예:
- Company(OpenAI) -[:RELATED_TO]-> Technology(GPT)

사용 시나리오:
- 특정 기업의 기술 흐름 분석
- 기업별 기술 포지션 비교

필수 여부:
- 선택


------------------------------------------------------------
Topic -[:RELATED_TO]-> Technology
------------------------------------------------------------

설명:
- 상위 주제와 구체 기술을 연결함

예:
- Topic(AI) -[:RELATED_TO]-> Technology(GPT)
- Topic(AI) -[:RELATED_TO]-> Technology(LLM)

사용 시나리오:
- "AI 뉴스" 요청 시 GPT/LLM/생성형AI 기사까지 확장 탐색

필수 여부:
- 권장


------------------------------------------------------------
UserIntent -[:INTERESTED_IN]-> Topic / Technology
------------------------------------------------------------

설명:
- 사용자가 관심 있어 하는 주제 또는 기술

예:
- UserIntent(Q001) -[:INTERESTED_IN]-> Topic(AI)
- UserIntent(Q002) -[:INTERESTED_IN]-> Technology(GPT)

사용 시나리오:
- "AI 관련"
- "GPT 관련"
- "클라우드 시장"

필수 여부:
- 발화에 관심 주제/기술이 있을 때 생성


------------------------------------------------------------
UserIntent -[:FOCUSES_ON]-> Company
------------------------------------------------------------

설명:
- 사용자 요청이 특정 기업에 초점을 둠

예:
- UserIntent(Q001) -[:FOCUSES_ON]-> Company(삼성)
- UserIntent(Q001) -[:FOCUSES_ON]-> Company(애플)

사용 시나리오:
- "삼성과 애플"
- "테슬라"
- "OpenAI"

필수 여부:
- 발화에 기업이 있을 때 생성


------------------------------------------------------------
UserIntent -[:REQUESTS]-> Event
------------------------------------------------------------

설명:
- 사용자가 원하는 뉴스 이벤트 유형

예:
- UserIntent(Q001) -[:REQUESTS]-> Event(업데이트)

사용 시나리오:
- 업데이트
- 투자
- 규제
- 사고
- 트렌드
- 비교분석

필수 여부:
- 이벤트 조건이 있을 때 생성


------------------------------------------------------------
UserIntent -[:FOR_AUDIENCE]-> Audience
------------------------------------------------------------

설명:
- 사용자 요청이 특정 관점/독자 유형을 기준으로 함

예:
- UserIntent(Q001) -[:FOR_AUDIENCE]-> Audience(개발자)

사용 시나리오:
- "개발자 입장에서"
- "창업자가 보면 좋을"
- "데이터 엔지니어링 관련"

필수 여부:
- 관점 조건이 있을 때 생성


------------------------------------------------------------
NewsArticle -[:RELATED_TO]-> Concept
------------------------------------------------------------

설명:
- 도메인 간 느슨한 연결을 위한 공통 의미 연결

예:
- NewsArticle(A001) -[:RELATED_TO]-> Concept(판교)

사용 시나리오:
- "판교 맛집과 판교 IT 뉴스 같이 보고 싶어"

필수 여부:
- 초기 구현에서는 선택
- 확장 구조에서는 권장

============================================================
4. IT 뉴스 도메인 최소 구현 스키마
============================================================

초기 구현에 반드시 필요한 노드:

1. NewsArticle
2. Topic
3. Technology
4. Company
5. Event
6. UserIntent

초기 구현에 선택적으로 추가할 노드:

1. Audience
2. Concept

초기 구현에 반드시 필요한 엣지:

1. NewsArticle -[:MENTIONS]-> Topic
2. NewsArticle -[:MENTIONS_TECH]-> Technology
3. NewsArticle -[:MENTIONS_COMPANY]-> Company
4. NewsArticle -[:DESCRIBES_EVENT]-> Event
5. UserIntent -[:INTERESTED_IN]-> Topic / Technology
6. UserIntent -[:FOCUSES_ON]-> Company
7. UserIntent -[:REQUESTS]-> Event

초기 구현에 선택적으로 추가할 엣지:

1. UserIntent -[:FOR_AUDIENCE]-> Audience
2. Topic -[:RELATED_TO]-> Technology
3. Company -[:RELATED_TO]-> Technology
4. NewsArticle -[:RELATED_TO]-> Concept

============================================================
5. IT 뉴스 그래프 탐색 기본 패턴
============================================================

------------------------------------------------------------
[패턴 01: Topic 기반 뉴스 탐색]
------------------------------------------------------------

예시 발화:
- "요즘 AI 관련해서 중요한 뉴스 뭐 있어?"

탐색 조건:
- NewsArticle -[:MENTIONS]-> Topic(AI)

보조 조건:
- NewsArticle.published_at 기준 최신순
- NewsArticle.importance_score 기준 중요도 정렬

반환:
- NewsArticle
- Topic
- 근거 Path


------------------------------------------------------------
[패턴 02: Technology + Event 기반 탐색]
------------------------------------------------------------

예시 발화:
- "최근 GPT 관련 업데이트 알려줘"

탐색 조건:
- NewsArticle -[:MENTIONS_TECH]-> Technology(GPT)
- NewsArticle -[:DESCRIBES_EVENT]-> Event(업데이트)

보조 조건:
- NewsArticle.published_at 기준 최신순

반환:
- NewsArticle
- Technology
- Event
- 근거 Path


------------------------------------------------------------
[패턴 03: Topic + Event 트렌드 분석]
------------------------------------------------------------

예시 발화:
- "클라우드 시장에서 요즘 트렌드 뭐야?"

탐색 조건:
- NewsArticle -[:MENTIONS]-> Topic(클라우드)
- NewsArticle -[:DESCRIBES_EVENT]-> Event(트렌드)

반환:
- NewsArticle 목록
- Topic
- Event
- 반복 등장 Technology 또는 Company
- 근거 Path


------------------------------------------------------------
[패턴 04: Company 비교]
------------------------------------------------------------

예시 발화:
- "삼성과 애플 최근 기술 경쟁 상황 어때?"

탐색 조건:
- NewsArticle -[:MENTIONS_COMPANY]-> Company(삼성)
- NewsArticle -[:MENTIONS_COMPANY]-> Company(애플)
- NewsArticle -[:DESCRIBES_EVENT]-> Event(기술경쟁)

반환:
- 두 기업을 모두 언급한 기사
- 또는 각 기업별 관련 기사 묶음
- Company
- Event
- 근거 Path

주의:
- 같은 기사에 두 기업이 모두 등장하는 경우와 각각 따로 등장하는 경우를 구분한다.


------------------------------------------------------------
[패턴 05: Audience 기반 필터링]
------------------------------------------------------------

예시 발화:
- "개발자 입장에서 중요한 IT 뉴스만 골라줘"

탐색 조건:
- UserIntent -[:FOR_AUDIENCE]-> Audience(개발자)
- UserIntent -[:INTERESTED_IN]-> Topic(IT)
- NewsArticle -[:MENTIONS]-> Topic(IT)

보조 조건:
- 개발자 관점과 관련 높은 Technology 우선
  - LLM
  - 오픈소스AI
  - 클라우드
  - 보안
  - 데이터엔지니어링
  - 프레임워크
  - API
  - 개발도구

주의:
- 초기 구현에서는 Audience를 직접 NewsArticle에 연결하지 않는다.
- Audience는 QueryBuilder에서 우선 탐색 Topic/Technology를 조정하는 조건으로 사용한다.


------------------------------------------------------------
[패턴 06: Event 기반 보안 사고 탐색]
------------------------------------------------------------

예시 발화:
- "보안 관련 사고 최근에 뭐 있었어?"

탐색 조건:
- NewsArticle -[:MENTIONS]-> Topic(보안)
- NewsArticle -[:DESCRIBES_EVENT]-> Event(보안사고)

보조 조건:
- published_at 최신순
- importance_score 높은 순

반환:
- NewsArticle
- Topic
- Event
- 근거 Path

============================================================
6. 설계상 중요한 결정
============================================================

1. NewsArticle은 결과 중심 노드다.

2. Topic, Technology, Company, Event는 탐색 조건 노드다.

3. Topic은 상위 분류, Technology는 구체 기술로 분리한다.

4. Event는 단순 키워드가 아니라 기사에서 설명하는 사건 유형이다.

5. Audience는 초기에는 UserIntent와 연결하고, QueryBuilder에서 필터링 보조 조건으로 사용한다.

6. 최신순, 중요도순, 신뢰도순 정렬은 Relationship이 아니라 NewsArticle Property를 사용한다.

7. Property 검색은 보조 수단이다.
   - published_at
   - importance_score
   - reliability_score
   - source
   - language

8. 핵심 탐색은 Relationship 기반으로 처리한다.

9. Restaurant과 NewsArticle은 직접 연결하지 않는다.

10. 도메인 간 연결이 필요하면 Concept 노드를 사용한다.

11. LLM은 기사 내용을 임의 생성하지 않고, 반환된 Article과 Path를 기반으로 요약한다.

============================================================
[STEP 04 결론]
============================================================

IT 뉴스 그래프 DB는 다음 구조로 확정한다.

핵심 결과 노드:
- NewsArticle

핵심 조건 노드:
- Topic
- Technology
- Company
- Event

공통 요청 노드:
- UserIntent

확장 노드:
- Audience
- Concept

핵심 탐색 관계:
- NewsArticle -[:MENTIONS]-> Topic
- NewsArticle -[:MENTIONS_TECH]-> Technology
- NewsArticle -[:MENTIONS_COMPANY]-> Company
- NewsArticle -[:DESCRIBES_EVENT]-> Event
- UserIntent -[:INTERESTED_IN]-> Topic / Technology
- UserIntent -[:FOCUSES_ON]-> Company
- UserIntent -[:REQUESTS]-> Event

확장 탐색 관계:
- UserIntent -[:FOR_AUDIENCE]-> Audience
- Topic -[:RELATED_TO]-> Technology
- Company -[:RELATED_TO]-> Technology
- NewsArticle -[:RELATED_TO]-> Concept

============================================================
[STEP 05] Neo4j 제약조건 / 인덱스 설계
============================================================

목표:
- 그래프 DB의 데이터 무결성과 성능을 동시에 확보한다.
- 중복 노드 생성 방지
- 빠른 탐색을 위한 인덱스 구조 확정
- 관계 탐색 중심 설계를 유지하면서 필요한 최소 Property 인덱스만 사용

============================================================
1. 설계 방향
============================================================

핵심 원칙:

1. 노드 중복 생성 방지 (UNIQUE CONSTRAINT 필수)
2. 정규화된 키 기반으로 MERGE 수행
3. 탐색은 Relationship 중심으로 수행
4. Property 인덱스는 "탐색 시작점"에만 사용
5. 정렬/필터 조건에 필요한 Property만 인덱스 생성
6. 모든 인덱스는 과도하게 만들지 않는다

============================================================
2. 제약조건 설계 (UNIQUE CONSTRAINT)
============================================================

------------------------------------------------------------
[Restaurant]
------------------------------------------------------------

CREATE CONSTRAINT restaurant_id_unique
IF NOT EXISTS
FOR (r:Restaurant)
REQUIRE r.restaurant_id IS UNIQUE;

CREATE CONSTRAINT restaurant_name_unique
IF NOT EXISTS
FOR (r:Restaurant)
REQUIRE r.name IS UNIQUE;

설명:
- restaurant_id는 시스템 내부 고유 키
- name은 초기 테스트 데이터에서는 중복 방지 용도로 사용

주의:
- 실제 서비스에서는 name만으로 UNIQUE는 위험 (동명 식당 존재 가능)
- production에서는 (name + address) 복합키 고려


------------------------------------------------------------
[Area]
------------------------------------------------------------

CREATE CONSTRAINT area_name_unique
IF NOT EXISTS
FOR (a:Area)
REQUIRE a.name IS UNIQUE;

설명:
- "강남", "홍대", "판교" 등 지역명은 중복 방지


------------------------------------------------------------
[Menu]
------------------------------------------------------------

CREATE CONSTRAINT menu_name_unique
IF NOT EXISTS
FOR (m:Menu)
REQUIRE m.normalized_name IS UNIQUE;

설명:
- "중국집", "중국음식", "중식" → normalized_name으로 통일


------------------------------------------------------------
[Ingredient]
------------------------------------------------------------

CREATE CONSTRAINT ingredient_name_unique
IF NOT EXISTS
FOR (i:Ingredient)
REQUIRE i.normalized_name IS UNIQUE;


------------------------------------------------------------
[Tag]
------------------------------------------------------------

CREATE CONSTRAINT tag_name_unique
IF NOT EXISTS
FOR (t:Tag)
REQUIRE t.normalized_name IS UNIQUE;


------------------------------------------------------------
[NewsArticle]
------------------------------------------------------------

CREATE CONSTRAINT article_id_unique
IF NOT EXISTS
FOR (n:NewsArticle)
REQUIRE n.article_id IS UNIQUE;

CREATE CONSTRAINT article_url_unique
IF NOT EXISTS
FOR (n:NewsArticle)
REQUIRE n.url IS UNIQUE;

설명:
- URL 기준 중복 제거가 핵심


------------------------------------------------------------
[Topic]
------------------------------------------------------------

CREATE CONSTRAINT topic_name_unique
IF NOT EXISTS
FOR (t:Topic)
REQUIRE t.normalized_name IS UNIQUE;


------------------------------------------------------------
[Technology]
------------------------------------------------------------

CREATE CONSTRAINT tech_name_unique
IF NOT EXISTS
FOR (t:Technology)
REQUIRE t.normalized_name IS UNIQUE;


------------------------------------------------------------
[Company]
------------------------------------------------------------

CREATE CONSTRAINT company_name_unique
IF NOT EXISTS
FOR (c:Company)
REQUIRE c.normalized_name IS UNIQUE;


------------------------------------------------------------
[Event]
------------------------------------------------------------

CREATE CONSTRAINT event_name_unique
IF NOT EXISTS
FOR (e:Event)
REQUIRE e.normalized_name IS UNIQUE;


------------------------------------------------------------
[Audience]
------------------------------------------------------------

CREATE CONSTRAINT audience_name_unique
IF NOT EXISTS
FOR (a:Audience)
REQUIRE a.normalized_name IS UNIQUE;


------------------------------------------------------------
[Concept]
------------------------------------------------------------

CREATE CONSTRAINT concept_name_unique
IF NOT EXISTS
FOR (c:Concept)
REQUIRE c.normalized_name IS UNIQUE;


============================================================
3. 인덱스 설계 (INDEX)
============================================================

------------------------------------------------------------
[Restaurant 인덱스]
------------------------------------------------------------

CREATE INDEX restaurant_rating_index
IF NOT EXISTS
FOR (r:Restaurant)
ON (r.rating);

CREATE INDEX restaurant_price_index
IF NOT EXISTS
FOR (r:Restaurant)
ON (r.avg_price);

설명:
- 정렬 및 가격 필터용
- WHERE + ORDER BY 최적화


------------------------------------------------------------
[NewsArticle 인덱스]
------------------------------------------------------------

CREATE INDEX article_date_index
IF NOT EXISTS
FOR (n:NewsArticle)
ON (n.published_at);

CREATE INDEX article_importance_index
IF NOT EXISTS
FOR (n:NewsArticle)
ON (n.importance_score);

CREATE INDEX article_reliability_index
IF NOT EXISTS
FOR (n:NewsArticle)
ON (n.reliability_score);

설명:
- 최신 뉴스 정렬
- 중요 뉴스 필터링


------------------------------------------------------------
[공통 탐색 시작점 인덱스]
------------------------------------------------------------

CREATE INDEX area_name_index
IF NOT EXISTS
FOR (a:Area)
ON (a.name);

CREATE INDEX menu_name_index
IF NOT EXISTS
FOR (m:Menu)
ON (m.normalized_name);

CREATE INDEX tag_name_index
IF NOT EXISTS
FOR (t:Tag)
ON (t.normalized_name);

CREATE INDEX topic_name_index
IF NOT EXISTS
FOR (t:Topic)
ON (t.normalized_name);

CREATE INDEX tech_name_index
IF NOT EXISTS
FOR (t:Technology)
ON (t.normalized_name);

설명:
- Slot → Node 매칭 속도 개선
- QueryBuilder에서 MATCH 시작점으로 사용


============================================================
4. MERGE 전략 (중요)
============================================================

노드 생성 시 반드시 MERGE 사용

------------------------------------------------------------
[나쁜 방식]
------------------------------------------------------------

CREATE (r:Restaurant {name: "강남파스타"})

문제:
- 중복 노드 생성됨


------------------------------------------------------------
[권장 방식]
------------------------------------------------------------

MERGE (r:Restaurant {restaurant_id: $restaurant_id})
ON CREATE SET
    r.name = $name,
    r.address = $address,
    r.created_at = timestamp()
ON MATCH SET
    r.updated_at = timestamp()

------------------------------------------------------------
[정규화 기반 MERGE]
------------------------------------------------------------

MERGE (m:Menu {normalized_name: $normalized_name})
ON CREATE SET
    m.name = $original_name

설명:
- "중국집", "중식", "중국음식" → 하나의 노드로 통합


============================================================
5. 관계 생성 전략
============================================================

------------------------------------------------------------
[기본 원칙]
------------------------------------------------------------

1. 관계도 반드시 MERGE 사용
2. 방향성 유지
3. 중복 관계 방지

------------------------------------------------------------
[예시]
------------------------------------------------------------

MATCH (r:Restaurant {restaurant_id: $rid})
MATCH (m:Menu {normalized_name: $menu})

MERGE (r)-[:SELLS]->(m)

------------------------------------------------------------
[부정 조건 대비]
------------------------------------------------------------

MATCH (ui:UserIntent {query_id: $qid})
MATCH (i:Ingredient {normalized_name: "면"})

MERGE (ui)-[:EXCLUDES]->(i)


============================================================
6. 성능 최적화 전략
============================================================

------------------------------------------------------------
[전략 01: 시작 노드 제한]
------------------------------------------------------------

- 항상 인덱스가 있는 노드에서 시작
- 예:
  MATCH (a:Area {name: "강남"})
  MATCH (m:Menu {normalized_name: "이탈리안"})


------------------------------------------------------------
[전략 02: Relationship 우선 탐색]
------------------------------------------------------------

- WHERE 절 대신 관계 사용

나쁜 방식:
- WHERE r.area = "강남"

좋은 방식:
- (r)-[:LOCATED_IN]->(a:Area {name: "강남"})


------------------------------------------------------------
[전략 03: 경로 길이 제한]
------------------------------------------------------------

- 불필요한 깊은 탐색 금지
- 2~3 depth 내에서 해결


------------------------------------------------------------
[전략 04: 결과 수 제한]
------------------------------------------------------------

- LIMIT 사용 필수

예:
- RETURN r LIMIT 20


------------------------------------------------------------
[전략 05: 부정 조건 처리]
------------------------------------------------------------

- NOT EXISTS 패턴 사용

예:
WHERE NOT EXISTS {
    MATCH (r)-[:SELLS]->(:Menu)-[:CONTAINS]->(:Ingredient {name:"면"})
}

============================================================
7. 최종 선택
============================================================

추천:
- [방안 03: 혼합 전략]

이유:
- 현재 단계는 테스트 + 확장 고려 단계
- 모든 인덱스를 다 만들 필요 없음
- 그러나 최소 인덱스만으로는 뉴스/추천 성능 부족 가능

============================================================
[STEP 05 결론]
============================================================

1. 모든 핵심 노드는 UNIQUE CONSTRAINT로 보호한다.
2. normalized_name 기반으로 중복을 제거한다.
3. 인덱스는 "시작 노드 + 정렬 필드" 중심으로 생성한다.
4. 모든 생성은 MERGE 기반으로 수행한다.
5. 탐색은 Property가 아니라 Relationship 중심으로 수행한다.
6. 부정 조건은 NOT EXISTS 패턴으로 처리한다.
7. 현재 프로젝트는 "혼합 인덱스 전략"을 사용한다.

============================================================
[STEP 05 보완] EXCLUDES 구체화 + Full-text Search 인덱스 추가
============================================================

결론:
- 기존 [방안 03: 혼합 전략]을 유지한다.
- 여기에 다음 2가지를 추가한다.

1. 부정 조건(EXCLUDES) 관계를 명확히 구체화한다.
2. 선택적으로 Full-text Search 인덱스를 추가한다.

============================================================
1. EXCLUDES 관계 구체화
============================================================

목표:
- "면은 싫어"
- "오이 빼줘"
- "된장 들어간 음식은 제외"
- "시끄러운 곳 말고"
- "웨이팅 긴 곳은 제외"

같은 부정 조건을 그래프 구조 안에서 명확히 표현한다.

------------------------------------------------------------
[EXCLUDES 기본 구조]
------------------------------------------------------------

UserIntent -[:EXCLUDES]-> Ingredient
UserIntent -[:EXCLUDES]-> Menu
UserIntent -[:EXCLUDES]-> Tag
UserIntent -[:EXCLUDES]-> Concept

예시:
- UserIntent(Q001) -[:EXCLUDES]-> Ingredient(면)
- UserIntent(Q002) -[:EXCLUDES]-> Ingredient(오이)
- UserIntent(Q003) -[:EXCLUDES]-> Tag(시끄러운)
- UserIntent(Q004) -[:EXCLUDES]-> Tag(웨이팅긴)

------------------------------------------------------------
[EXCLUDES 관계 속성]
------------------------------------------------------------

EXCLUDES 관계에는 다음 속성을 둘 수 있다.

- reason_text
  - 사용자가 말한 원문 부정 표현
  - 예: "면은 싫어", "오이 빼줘"

- exclude_type
  - ingredient
  - menu
  - tag
  - concept

- strength
  - hard
  - soft

- created_at

예시:
UserIntent(Q001)
-[:EXCLUDES {
    reason_text: "면은 싫어",
    exclude_type: "ingredient",
    strength: "hard"
}]->
Ingredient(면)

------------------------------------------------------------
[hard / soft 구분]
------------------------------------------------------------

hard:
- 절대 제외
- 알레르기, 싫어함, 금지 조건, 명시적 제외
- 예:
  - "오이 빼줘"
  - "면은 싫어"
  - "된장 들어간 음식은 제외"

soft:
- 가능하면 제외
- 선호도에 가까운 부정 조건
- 예:
  - "너무 시끄러운 곳은 별로"
  - "웨이팅 긴 곳은 피하고 싶어"

초기 구현 추천:
- 명시적 부정 표현은 hard로 처리한다.
- 애매한 부정 표현은 soft로 처리하거나 clarification 대상으로 보낸다.

------------------------------------------------------------
[EXCLUDES 탐색 방식]
------------------------------------------------------------

예시 01:
"면은 싫은데 중국집 가고 싶어"

탐색:
1. 중국음식 판매 식당 탐색
2. 면 Ingredient와 연결된 Menu 제외
3. 남은 메뉴 또는 식당 반환

Cypher 개념:
MATCH (r:Restaurant)-[:SELLS]->(m:Menu {normalized_name:"중국음식"})
WHERE NOT EXISTS {
    MATCH (m)-[:CONTAINS]->(:Ingredient {normalized_name:"면"})
}
RETURN r, m

주의:
- "중국음식"이 카테고리 Menu이고, 짜장면/짬뽕 같은 개별 메뉴가 별도 Menu라면
  Restaurant -[:SELLS]-> Menu(짜장면)
  Menu(짜장면) -[:BELONGS_TO]-> Menu(중국음식)
  구조를 추가로 고려할 수 있다.

예시 02:
"시끄러운 곳 말고 조용한 카페 알려줘"

탐색:
1. 카페 판매/분류 식당 탐색
2. 조용한 Tag 포함
3. 시끄러운 Tag 제외

Cypher 개념:
MATCH (r:Restaurant)-[:SELLS]->(:Menu {normalized_name:"카페"})
MATCH (r)-[:HAS_TAG]->(:Tag {normalized_name:"조용한"})
WHERE NOT EXISTS {
    MATCH (r)-[:HAS_TAG]->(:Tag {normalized_name:"시끄러운"})
}
RETURN r

============================================================
2. Full-text Search 인덱스 추가
============================================================

목표:
- normalized_name만으로 매칭이 어려운 경우를 보완한다.
- 뉴스 제목, 기사 본문, 식당 설명, 태그 설명 등에서 유사 키워드 검색을 가능하게 한다.
- LLM이 무리하게 키워드를 추론하지 않도록 DB 검색 보조 장치를 둔다.

------------------------------------------------------------
[사용 목적]
------------------------------------------------------------

Full-text Search는 핵심 탐색 수단이 아니다.
보조 탐색 수단이다.

사용하는 경우:
1. Slot 정규화 실패
2. 사용자가 애매한 표현 사용
3. 뉴스 제목/본문에서 유사 키워드 탐색 필요
4. 식당 설명문에서 태그 후보 추출 필요
5. 초기 데이터에 관계가 충분히 구축되지 않은 경우

사용하지 않는 경우:
1. 이미 정확한 normalized_name 매칭이 가능한 경우
2. 관계 탐색으로 충분한 경우
3. 핵심 추천 로직 전체를 텍스트 검색에 의존하는 경우

------------------------------------------------------------
[추천 Full-text Index]
------------------------------------------------------------

1) 식당 검색용

CREATE FULLTEXT INDEX restaurant_text_index
IF NOT EXISTS
FOR (r:Restaurant)
ON EACH [r.name, r.address, r.description];

사용 목적:
- 식당명 유사 검색
- 주소/설명 기반 검색
- 설명글에서 분위기 후보 탐색

주의:
- Restaurant.description 속성이 없다면 추가하거나 생략한다.


2) 메뉴/태그/재료 검색용

CREATE FULLTEXT INDEX food_condition_text_index
IF NOT EXISTS
FOR (n:Menu|Tag|Ingredient)
ON EACH [n.name, n.normalized_name];

사용 목적:
- "중국집", "중식", "중국음식" 같은 표현 보완
- "맵다", "매운맛", "칼칼한" 같은 태그 후보 탐색
- "면", "국수", "누들" 같은 재료/메뉴 후보 탐색


3) 뉴스 검색용

CREATE FULLTEXT INDEX news_text_index
IF NOT EXISTS
FOR (n:NewsArticle)
ON EACH [n.title, n.summary, n.content];

사용 목적:
- 뉴스 제목/요약/본문 유사 검색
- Topic/Technology/Event 관계가 부족한 초기 데이터 보완
- RAG 검색 전 후보 기사 축소


4) 뉴스 조건 노드 검색용

CREATE FULLTEXT INDEX news_condition_text_index
IF NOT EXISTS
FOR (n:Topic|Technology|Company|Event)
ON EACH [n.name, n.normalized_name];

사용 목적:
- GPT, ChatGPT, 생성형AI, LLM 등 유사 표현 보완
- 기업명 영문/한글 표현 보완
- 이벤트명 유사 표현 보완

============================================================
3. Full-text Search 사용 흐름
============================================================

기본 흐름:

1. SlotExtractor가 normalized_name 생성
2. 정확 매칭 시도
3. 정확 매칭 실패 시 Full-text Search 실행
4. 후보 노드 반환
5. confidence 기준으로 자동 선택 또는 clarification
6. 선택된 노드 기준으로 Relationship 탐색 수행

예시:
사용자 발화:
- "요즘 챗지피티 업데이트 있어?"

정확 매칭:
- 챗지피티 → Technology(ChatGPT) 없음

Full-text Search:
- GPT
- ChatGPT
- OpenAI GPT

결과:
- Technology(GPT) 후보 선택

이후 탐색:
- NewsArticle -[:MENTIONS_TECH]-> Technology(GPT)
- NewsArticle -[:DESCRIBES_EVENT]-> Event(업데이트)

============================================================
4. 최종 반영된 STEP 05 전략
============================================================

기존 선택:
- [방안 03: 혼합 전략]

보완 후 최종 전략:
- [방안 03-A: Relationship 중심 혼합 전략 + EXCLUDES 구체화 + Full-text 보조 검색]

특징:
- Relationship 탐색을 기본으로 한다.
- Property 인덱스는 시작점과 정렬 필드에만 둔다.
- 부정 조건은 UserIntent -[:EXCLUDES]-> Node 관계로 명확히 표현한다.
- Full-text Search는 정규화 실패나 유사 키워드 탐색의 보조 수단으로만 사용한다.

장점:
- 그래프 DB의 장점을 유지한다.
- 부정 조건 처리가 명확하다.
- LLM의 임의 추론 부담이 줄어든다.
- 초기 데이터 품질이 완벽하지 않아도 검색 안정성이 올라간다.

단점:
- Full-text Search 결과를 다시 검증해야 한다.
- 유사 키워드가 많으면 clarification이 필요할 수 있다.
- EXCLUDES 관계를 저장할 경우 query_id 단위 UserIntent 관리가 필요하다.

실무적 제언:
- 현재 프로젝트에는 이 방식이 가장 적합하다.
- 유저 200명 내외의 초기 KAG 테스트라면 성능 부담보다 검색 안정성이 더 중요하다.
- 단, Full-text Search를 메인 검색으로 쓰면 그래프 DB 설계 의미가 약해진다.
- 따라서 Full-text Search는 반드시 "보조 검색"으로 제한한다.

============================================================
[STEP 05 최종 결론]
============================================================

1. STEP 05의 최종 선택은 [방안 03-A]로 확정한다.

2. 핵심 탐색은 Relationship 기반으로 유지한다.

3. Property Index는 시작 노드와 정렬 필드에만 둔다.

4. EXCLUDES 관계는 hard / soft 속성을 포함해 구체화한다.

5. 명시적 부정 조건은 hard EXCLUDES로 처리한다.

6. 애매한 부정 조건은 soft EXCLUDES 또는 clarification으로 처리한다.

7. Full-text Search Index는 선택적으로 둔다.

8. Full-text Search는 정규화 실패, 유사 키워드 검색, 초기 데이터 보완 용도로만 사용한다.

9. Full-text Search 결과는 바로 최종 결과로 쓰지 않고, Relationship 탐색의 시작 후보로만 사용한다.

10. 다음 단계에서는 이 구조를 기준으로 [STEP 06: 샘플 데이터 설계]를 진행한다.

============================================================
[STEP 06] 샘플 데이터 설계
============================================================

목표:
- Neo4j에 넣을 최소 샘플 데이터를 설계한다.
- 맛집 / IT 뉴스 각각의 테스트 시나리오를 검증할 수 있어야 한다.
- 대량 데이터가 아니라 “쿼리 검증용 최소 데이터셋”을 만든다.

============================================================
1. 샘플 데이터 설계 원칙
============================================================

1. 모든 샘플 데이터는 테스트 시나리오를 검증하기 위한 목적이다.

2. 노드 수를 과하게 늘리지 않는다.

3. 긍정 조건과 부정 조건을 모두 검증할 수 있어야 한다.

4. Relationship 탐색이 가능하도록 노드와 엣지를 반드시 함께 만든다.

5. Full-text Search는 보조 검증용으로만 사용한다.

6. Restaurant과 NewsArticle은 직접 연결하지 않는다.

7. 도메인 간 연결은 Concept 노드로만 테스트한다.

============================================================
2. 맛집 샘플 데이터
============================================================

------------------------------------------------------------
[Restaurant 노드]
------------------------------------------------------------

1. R001
- name: 강남파스타
- address: 서울 강남구
- rating: 4.5
- review_count: 320
- avg_price: 18000
- description: 강남에서 분위기 좋은 이탈리안 레스토랑

2. R002
- name: 홍대초밥
- address: 서울 마포구 홍대
- rating: 4.4
- review_count: 210
- avg_price: 15000
- description: 가성비 좋은 초밥집

3. R003
- name: 을지로고기집
- address: 서울 중구 을지로
- rating: 4.3
- review_count: 540
- avg_price: 22000
- description: 회식하기 좋은 고기집

4. R004
- name: 조용한카페
- address: 서울 성동구
- rating: 4.6
- review_count: 180
- avg_price: 9000
- description: 조용하고 깔끔한 카페

5. R005
- name: 홍콩반점
- address: 서울 강남구
- rating: 4.1
- review_count: 430
- avg_price: 9000
- description: 중국음식 전문점

6. R006
- name: 담백한고기집
- address: 경기 성남시 판교
- rating: 4.5
- review_count: 260
- avg_price: 19000
- description: 기름지지 않고 담백한 고기 메뉴 제공

7. R007
- name: 건강한한식
- address: 서울 종로구
- rating: 4.2
- review_count: 150
- avg_price: 12000
- description: 운동 후 먹기 좋은 건강식 한식집

8. R008
- name: 야간분식
- address: 서울 강남구
- rating: 4.0
- review_count: 390
- avg_price: 8000
- description: 늦은 밤에도 영업하는 분식집


------------------------------------------------------------
[Area 노드]
------------------------------------------------------------

1. 강남
2. 홍대
3. 을지로
4. 성동
5. 판교
6. 종로


------------------------------------------------------------
[Menu 노드]
------------------------------------------------------------

1. 이탈리안
- menu_type: category

2. 파스타
- menu_type: dish

3. 초밥
- menu_type: dish

4. 고기
- menu_type: category

5. 카페
- menu_type: category

6. 중국음식
- menu_type: category

7. 짜장면
- menu_type: dish

8. 짬뽕
- menu_type: dish

9. 한식
- menu_type: category

10. 된장찌개
- menu_type: dish

11. 건강식
- menu_type: category

12. 분식
- menu_type: category


------------------------------------------------------------
[Ingredient 노드]
------------------------------------------------------------

1. 면
2. 된장
3. 고기
4. 기름진음식
5. 오이


------------------------------------------------------------
[Tag 노드]
------------------------------------------------------------

1. 분위기좋은
- tag_type: mood

2. 가성비
- tag_type: price_signal

3. 회식
- tag_type: situation

4. 조용한
- tag_type: mood

5. 시끄러운
- tag_type: negative_signal

6. 혼밥가능
- tag_type: situation

7. 담백한
- tag_type: taste

8. 기름진음식
- tag_type: negative_signal

9. 건강식
- tag_type: taste

10. 야간영업
- tag_type: operation

11. 깔끔한
- tag_type: mood

12. 배달가능
- tag_type: service

13. 웨이팅긴
- tag_type: negative_signal

14. 어른동반적합
- tag_type: situation


------------------------------------------------------------
[맛집 관계 데이터]
------------------------------------------------------------

1. 강남파스타
- LOCATED_IN -> 강남
- SELLS -> 이탈리안
- SELLS -> 파스타
- HAS_TAG -> 분위기좋은
- HAS_TAG -> 데이트
- HAS_TAG -> 깔끔한
- RELATED_TO -> Concept(강남)

2. 홍대초밥
- LOCATED_IN -> 홍대
- SELLS -> 초밥
- HAS_TAG -> 가성비
- HAS_TAG -> 혼밥가능

3. 을지로고기집
- LOCATED_IN -> 을지로
- SELLS -> 고기
- HAS_TAG -> 회식
- HAS_TAG -> 웨이팅긴

4. 조용한카페
- LOCATED_IN -> 성동
- SELLS -> 카페
- HAS_TAG -> 조용한
- HAS_TAG -> 깔끔한
- HAS_TAG -> 어른동반적합

5. 홍콩반점
- LOCATED_IN -> 강남
- SELLS -> 중국음식
- SELLS -> 짜장면
- SELLS -> 짬뽕
- HAS_TAG -> 가성비
- HAS_TAG -> 혼밥가능

6. 담백한고기집
- LOCATED_IN -> 판교
- SELLS -> 고기
- HAS_TAG -> 담백한
- HAS_TAG -> 회식
- RELATED_TO -> Concept(판교)

7. 건강한한식
- LOCATED_IN -> 종로
- SELLS -> 한식
- SELLS -> 된장찌개
- SELLS -> 건강식
- HAS_TAG -> 건강식
- HAS_TAG -> 깔끔한

8. 야간분식
- LOCATED_IN -> 강남
- SELLS -> 분식
- HAS_TAG -> 야간영업
- HAS_TAG -> 배달가능


------------------------------------------------------------
[Menu - Ingredient 관계]
------------------------------------------------------------

1. 파스타 -[:CONTAINS]-> 면
2. 짜장면 -[:CONTAINS]-> 면
3. 짬뽕 -[:CONTAINS]-> 면
4. 된장찌개 -[:CONTAINS]-> 된장
5. 고기 -[:CONTAINS]-> 고기
6. 초밥 -[:CONTAINS]-> 오이

============================================================
3. IT 뉴스 샘플 데이터
============================================================

------------------------------------------------------------
[NewsArticle 노드]
------------------------------------------------------------

1. A001
- title: OpenAI GPT 업데이트 공개
- summary: OpenAI가 GPT 관련 기능 업데이트를 공개했다.
- source: TechDaily
- url: https://example.com/news/a001
- published_at: 2026-05-01
- importance_score: 0.91
- reliability_score: 0.88

2. A002
- title: 클라우드 시장에서 AI 인프라 경쟁 심화
- summary: 주요 클라우드 기업들이 AI 인프라 투자를 확대하고 있다.
- source: ITNews
- url: https://example.com/news/a002
- published_at: 2026-04-28
- importance_score: 0.87
- reliability_score: 0.84

3. A003
- title: 삼성과 애플의 온디바이스 AI 경쟁
- summary: 삼성과 애플이 모바일 AI 기술 경쟁을 강화하고 있다.
- source: DigitalTimes
- url: https://example.com/news/a003
- published_at: 2026-04-25
- importance_score: 0.85
- reliability_score: 0.82

4. A004
- title: 생성형 AI 규제 논의 확대
- summary: 각국 정부가 생성형 AI 규제 프레임워크를 논의하고 있다.
- source: PolicyTech
- url: https://example.com/news/a004
- published_at: 2026-04-20
- importance_score: 0.89
- reliability_score: 0.86

5. A005
- title: 보안 업계 대규모 데이터 유출 사고 대응
- summary: 보안 기업들이 최근 데이터 유출 사고에 대한 대응책을 발표했다.
- source: SecurityNews
- url: https://example.com/news/a005
- published_at: 2026-04-18
- importance_score: 0.88
- reliability_score: 0.83

6. A006
- title: 판교 스타트업 투자 회복 조짐
- summary: 판교 지역 스타트업을 중심으로 투자 회복 신호가 나타나고 있다.
- source: StartupBrief
- url: https://example.com/news/a006
- published_at: 2026-04-16
- importance_score: 0.76
- reliability_score: 0.79


------------------------------------------------------------
[Topic 노드]
------------------------------------------------------------

1. AI
2. 클라우드
3. 반도체
4. 보안
5. 스타트업
6. 데이터엔지니어링
7. IT


------------------------------------------------------------
[Technology 노드]
------------------------------------------------------------

1. GPT
2. 생성형AI
3. LLM
4. GPU
5. 온디바이스AI
6. 클라우드인프라


------------------------------------------------------------
[Company 노드]
------------------------------------------------------------

1. OpenAI
2. Google
3. Microsoft
4. 삼성
5. 애플
6. 테슬라


------------------------------------------------------------
[Event 노드]
------------------------------------------------------------

1. 업데이트
2. 투자
3. 규제
4. 보안사고
5. 트렌드
6. 기술경쟁
7. 투자회복


------------------------------------------------------------
[Audience 노드]
------------------------------------------------------------

1. 개발자
2. 창업자
3. 데이터엔지니어


------------------------------------------------------------
[IT 뉴스 관계 데이터]
------------------------------------------------------------

1. A001
- MENTIONS -> Topic(AI)
- MENTIONS_TECH -> Technology(GPT)
- MENTIONS_TECH -> Technology(LLM)
- MENTIONS_COMPANY -> Company(OpenAI)
- DESCRIBES_EVENT -> Event(업데이트)
- RELATED_TO -> Concept(AI)

2. A002
- MENTIONS -> Topic(클라우드)
- MENTIONS -> Topic(AI)
- MENTIONS_TECH -> Technology(클라우드인프라)
- MENTIONS_TECH -> Technology(GPU)
- MENTIONS_COMPANY -> Company(Google)
- MENTIONS_COMPANY -> Company(Microsoft)
- DESCRIBES_EVENT -> Event(투자)
- DESCRIBES_EVENT -> Event(트렌드)

3. A003
- MENTIONS -> Topic(AI)
- MENTIONS_TECH -> Technology(온디바이스AI)
- MENTIONS_COMPANY -> Company(삼성)
- MENTIONS_COMPANY -> Company(애플)
- DESCRIBES_EVENT -> Event(기술경쟁)

4. A004
- MENTIONS -> Topic(AI)
- MENTIONS_TECH -> Technology(생성형AI)
- DESCRIBES_EVENT -> Event(규제)

5. A005
- MENTIONS -> Topic(보안)
- DESCRIBES_EVENT -> Event(보안사고)

6. A006
- MENTIONS -> Topic(스타트업)
- MENTIONS_COMPANY -> Company(스타트업)
- DESCRIBES_EVENT -> Event(투자회복)
- RELATED_TO -> Concept(판교)


============================================================
4. Concept 샘플 데이터
============================================================

------------------------------------------------------------
[Concept 노드]
------------------------------------------------------------

1. 판교
- concept_type: location

2. AI
- concept_type: technology_area

3. 스타트업
- concept_type: industry

4. 개발자
- concept_type: audience

5. 강남
- concept_type: location


------------------------------------------------------------
[Concept 관계 테스트]
------------------------------------------------------------

1. 담백한고기집 -[:RELATED_TO]-> Concept(판교)
2. A006 -[:RELATED_TO]-> Concept(판교)

검증 목적:
- "판교 맛집과 판교 IT 뉴스 같이 볼 수 있어?"
- Restaurant과 NewsArticle을 직접 연결하지 않고 Concept을 통해 느슨하게 연결한다.

============================================================
5. UserIntent 샘플 데이터
============================================================

------------------------------------------------------------
[UserIntent 예시 01: 맛집 부정 조건]
------------------------------------------------------------

query_id: Q001
domain: restaurant
intent: restaurant_exclusion_search
raw_text: "면은 싫은데 중국집 가고 싶어"

관계:
- Q001 -[:PREFERS]-> Menu(중국음식)
- Q001 -[:EXCLUDES {
    exclude_type: "ingredient",
    strength: "hard",
    reason_text: "면은 싫은데"
  }]-> Ingredient(면)


------------------------------------------------------------
[UserIntent 예시 02: 맛집 태그 제외]
------------------------------------------------------------

query_id: Q002
domain: restaurant
intent: restaurant_exclusion_search
raw_text: "시끄러운 곳 말고 조용한 카페 알려줘"

관계:
- Q002 -[:PREFERS]-> Menu(카페)
- Q002 -[:REQUIRES]-> Tag(조용한)
- Q002 -[:EXCLUDES {
    exclude_type: "tag",
    strength: "hard",
    reason_text: "시끄러운 곳 말고"
  }]-> Tag(시끄러운)


------------------------------------------------------------
[UserIntent 예시 03: IT 뉴스 기술 업데이트]
------------------------------------------------------------

query_id: Q003
domain: it_news
intent: news_event_search
raw_text: "최근 GPT 관련 업데이트 알려줘"

관계:
- Q003 -[:INTERESTED_IN]-> Technology(GPT)
- Q003 -[:REQUESTS]-> Event(업데이트)


------------------------------------------------------------
[UserIntent 예시 04: IT 뉴스 기업 비교]
------------------------------------------------------------

query_id: Q004
domain: it_news
intent: news_comparison
raw_text: "삼성과 애플 최근 기술 경쟁 상황 어때?"

관계:
- Q004 -[:FOCUSES_ON]-> Company(삼성)
- Q004 -[:FOCUSES_ON]-> Company(애플)
- Q004 -[:REQUESTS]-> Event(기술경쟁)


------------------------------------------------------------
[UserIntent 예시 05: Concept 연결]
------------------------------------------------------------

query_id: Q005
domain: mixed
intent: concept_bridge_search
raw_text: "판교 맛집이랑 판교 IT 뉴스 같이 보고 싶어"

관계:
- Q005 -[:INTERESTED_IN]-> Concept(판교)

============================================================
6. 샘플 데이터 검증 시나리오
============================================================

------------------------------------------------------------
[시나리오 01]
------------------------------------------------------------

발화:
- "면은 싫은데 중국집 가고 싶어"

기대 결과:
- 홍콩반점은 중국음식 식당으로 후보가 된다.
- 단, 짜장면/짬뽕은 면을 포함하므로 메뉴 단위에서는 제외된다.
- 식당 단위 추천 시에는 "면 없는 메뉴 확인 필요" 경고가 필요하다.

검증 관계:
- UserIntent -[:EXCLUDES]-> Ingredient(면)
- Restaurant -[:SELLS]-> Menu(중국음식)
- Menu(짜장면) -[:CONTAINS]-> Ingredient(면)


------------------------------------------------------------
[시나리오 02]
------------------------------------------------------------

발화:
- "시끄러운 곳 말고 조용한 카페 알려줘"

기대 결과:
- 조용한카페 반환
- 시끄러운 Tag가 있는 식당 제외

검증 관계:
- Restaurant -[:SELLS]-> Menu(카페)
- Restaurant -[:HAS_TAG]-> Tag(조용한)
- UserIntent -[:EXCLUDES]-> Tag(시끄러운)


------------------------------------------------------------
[시나리오 03]
------------------------------------------------------------

발화:
- "최근 GPT 관련 업데이트 알려줘"

기대 결과:
- A001 반환

검증 관계:
- NewsArticle(A001) -[:MENTIONS_TECH]-> Technology(GPT)
- NewsArticle(A001) -[:DESCRIBES_EVENT]-> Event(업데이트)


------------------------------------------------------------
[시나리오 04]
------------------------------------------------------------

발화:
- "삼성과 애플 최근 기술 경쟁 상황 어때?"

기대 결과:
- A003 반환

검증 관계:
- NewsArticle(A003) -[:MENTIONS_COMPANY]-> Company(삼성)
- NewsArticle(A003) -[:MENTIONS_COMPANY]-> Company(애플)
- NewsArticle(A003) -[:DESCRIBES_EVENT]-> Event(기술경쟁)


------------------------------------------------------------
[시나리오 05]
------------------------------------------------------------

발화:
- "판교 맛집이랑 판교 IT 뉴스 같이 보고 싶어"

기대 결과:
- Restaurant: 담백한고기집
- NewsArticle: A006
- 연결 근거:
  - 둘 다 Concept(판교)와 RELATED_TO 관계를 가진다.

검증 관계:
- Restaurant -[:RELATED_TO]-> Concept(판교)
- NewsArticle -[:RELATED_TO]-> Concept(판교)

============================================================
7. STEP 06 최종 결정
============================================================

샘플 데이터는 다음 규모로 시작한다.

맛집:
- Restaurant 8개
- Area 6개
- Menu 12개
- Ingredient 5개
- Tag 14개

IT 뉴스:
- NewsArticle 6개
- Topic 7개
- Technology 6개
- Company 6개
- Event 7개
- Audience 3개

공통:
- Concept 5개
- UserIntent 5개

이 데이터셋으로 다음을 검증한다.

1. 관계 기반 추천
2. 부정 조건 EXCLUDES
3. Ingredient 제외
4. Tag 제외
5. Topic 기반 뉴스 탐색
6. Technology + Event 탐색
7. Company 비교
8. Concept 기반 도메인 간 느슨한 연결
9. Full-text Search 보조 검색 가능성
10. LLM Path 해석 가능성

============================================================
[STEP 06 결론]
============================================================

샘플 데이터는 대량 구축이 아니라 테스트 가능한 최소 그래프 구축을 목표로 한다.

============================================================
[STEP 07] Cypher 쿼리 패턴 설계
============================================================

목표:
- STEP 06 샘플 데이터를 기준으로 실제 Neo4j에서 실행 가능한 탐색 패턴을 설계한다.
- 맛집 / IT 뉴스 / Concept 연결 / EXCLUDES 부정 조건 / Full-text 보조 검색을 검증한다.

============================================================
1. Cypher 쿼리 설계 원칙
============================================================

1. Relationship 탐색을 우선한다.

2. Property 조건은 보조적으로만 사용한다.
   - 가격
   - 평점
   - 최신순
   - 중요도순
   - 신뢰도순

3. 모든 검색 결과는 결과 노드만 반환하지 않는다.
   - 결과 노드
   - 연결된 조건 노드
   - 근거 관계
   - Path 설명에 필요한 데이터
   를 함께 반환한다.

4. LIMIT는 반드시 사용한다.

5. 부정 조건은 EXCLUDES 관계와 NOT EXISTS 패턴을 함께 사용한다.

6. Full-text Search는 정확 매칭 실패 시 보조 후보 탐색으로만 사용한다.

============================================================
2. 맛집 쿼리 패턴
============================================================

------------------------------------------------------------
[패턴 01: 지역 + 메뉴 + 태그 추천]
------------------------------------------------------------

사용 예:
- "강남에서 분위기 좋은 이탈리안 레스토랑 추천해줘"

Cypher:

MATCH (a:Area {name: $area_name})
MATCH (m:Menu {normalized_name: $menu_name})
MATCH (t:Tag {normalized_name: $tag_name})
MATCH path_area = (r:Restaurant)-[:LOCATED_IN]->(a)
MATCH path_menu = (r)-[:SELLS]->(m)
MATCH path_tag = (r)-[:HAS_TAG]->(t)
RETURN
    r AS restaurant,
    a AS area,
    m AS menu,
    t AS tag,
    [path_area, path_menu, path_tag] AS evidence_paths
ORDER BY
    r.rating DESC,
    r.review_count DESC
LIMIT 10;

필수 파라미터:
- area_name
- menu_name
- tag_name

예시 파라미터:
- area_name: 강남
- menu_name: 이탈리안
- tag_name: 분위기좋은

기대 결과:
- 강남파스타


------------------------------------------------------------
[패턴 02: 메뉴 기반 추천]
------------------------------------------------------------

사용 예:
- "초밥집 추천해줘"

Cypher:

MATCH (m:Menu {normalized_name: $menu_name})
MATCH path_menu = (r:Restaurant)-[:SELLS]->(m)
OPTIONAL MATCH path_area = (r)-[:LOCATED_IN]->(a:Area)
OPTIONAL MATCH path_tag = (r)-[:HAS_TAG]->(t:Tag)
RETURN
    r AS restaurant,
    m AS menu,
    collect(DISTINCT a) AS areas,
    collect(DISTINCT t) AS tags,
    collect(DISTINCT path_area) + collect(DISTINCT path_tag) + [path_menu] AS evidence_paths
ORDER BY
    r.rating DESC,
    r.review_count DESC
LIMIT 10;

필수 파라미터:
- menu_name

예시 파라미터:
- menu_name: 초밥

기대 결과:
- 홍대초밥


------------------------------------------------------------
[패턴 03: 메뉴 + 부정 재료 제외]
------------------------------------------------------------

사용 예:
- "면은 싫은데 중국집 가고 싶어"

Cypher:

MATCH (preferred:Menu {normalized_name: $menu_name})
MATCH (excluded:Ingredient {normalized_name: $excluded_ingredient})
MATCH path_menu = (r:Restaurant)-[:SELLS]->(preferred)
WHERE NOT EXISTS {
    MATCH (r)-[:SELLS]->(sold:Menu)-[:CONTAINS]->(excluded)
}
RETURN
    r AS restaurant,
    preferred AS preferred_menu,
    excluded AS excluded_ingredient,
    [path_menu] AS evidence_paths
ORDER BY
    r.rating DESC,
    r.review_count DESC
LIMIT 10;

필수 파라미터:
- menu_name
- excluded_ingredient

예시 파라미터:
- menu_name: 중국음식
- excluded_ingredient: 면

주의:
- 이 쿼리는 식당이 판매하는 다른 메뉴 중 하나라도 면을 포함하면 식당 전체를 제외한다.
- 초기에는 안전한 방식이다.
- 단, 중국집 전체가 제외될 수 있다.

대안:
- 메뉴 단위 추천으로 분리할 수 있다.


------------------------------------------------------------
[패턴 03-B: 메뉴 단위 부정 재료 제외]
------------------------------------------------------------

사용 예:
- "면은 싫은데 중국집에서 뭐 먹을 수 있어?"

Cypher:

MATCH (category:Menu {normalized_name: $menu_name})
MATCH (excluded:Ingredient {normalized_name: $excluded_ingredient})
MATCH (r:Restaurant)-[:SELLS]->(category)
MATCH path_menu = (r)-[:SELLS]->(candidate:Menu)
WHERE candidate <> category
AND NOT EXISTS {
    MATCH (candidate)-[:CONTAINS]->(excluded)
}
RETURN
    r AS restaurant,
    category AS requested_category,
    candidate AS available_menu,
    excluded AS excluded_ingredient,
    [path_menu] AS evidence_paths
ORDER BY
    r.rating DESC,
    r.review_count DESC
LIMIT 10;

필수 파라미터:
- menu_name
- excluded_ingredient

예시 파라미터:
- menu_name: 중국음식
- excluded_ingredient: 면

기대 결과:
- 홍콩반점은 중국음식 식당으로 후보
- 면이 없는 candidate menu만 반환
- 현재 샘플 데이터에서는 짜장면/짬뽕이 면 포함이라 결과가 없을 수 있음

실무적 제언:
- "식당 추천"과 "메뉴 추천"을 분리해야 한다.
- 부정 재료 조건이 있으면 메뉴 단위 검증이 더 안전하다.


------------------------------------------------------------
[패턴 04: 긍정 태그 + 부정 태그 제외]
------------------------------------------------------------

사용 예:
- "시끄러운 곳 말고 조용한 카페 알려줘"

Cypher:

MATCH (m:Menu {normalized_name: $menu_name})
MATCH (required:Tag {normalized_name: $required_tag})
MATCH (excluded:Tag {normalized_name: $excluded_tag})
MATCH path_menu = (r:Restaurant)-[:SELLS]->(m)
MATCH path_required = (r)-[:HAS_TAG]->(required)
WHERE NOT EXISTS {
    MATCH (r)-[:HAS_TAG]->(excluded)
}
RETURN
    r AS restaurant,
    m AS menu,
    required AS required_tag,
    excluded AS excluded_tag,
    [path_menu, path_required] AS evidence_paths
ORDER BY
    r.rating DESC,
    r.review_count DESC
LIMIT 10;

필수 파라미터:
- menu_name
- required_tag
- excluded_tag

예시 파라미터:
- menu_name: 카페
- required_tag: 조용한
- excluded_tag: 시끄러운

기대 결과:
- 조용한카페


------------------------------------------------------------
[패턴 05: 가격 조건 검색]
------------------------------------------------------------

사용 예:
- "혼자 가기 편한 한식집 중에 가격 1만원 이하로 알려줘"

Cypher:

MATCH (m:Menu {normalized_name: $menu_name})
MATCH (t:Tag {normalized_name: $tag_name})
MATCH path_menu = (r:Restaurant)-[:SELLS]->(m)
MATCH path_tag = (r)-[:HAS_TAG]->(t)
WHERE r.avg_price <= $max_price
RETURN
    r AS restaurant,
    m AS menu,
    t AS tag,
    r.avg_price AS avg_price,
    [path_menu, path_tag] AS evidence_paths
ORDER BY
    r.rating DESC,
    r.review_count DESC
LIMIT 10;

필수 파라미터:
- menu_name
- tag_name
- max_price

예시 파라미터:
- menu_name: 한식
- tag_name: 혼밥가능
- max_price: 10000

주의:
- 가격은 Relationship만으로 처리하기 어렵기 때문에 Property 조건을 사용한다.


------------------------------------------------------------
[패턴 06: 상황 기반 추천]
------------------------------------------------------------

사용 예:
- "부모님 모시고 갈 수 있는 깔끔한 식당 알려줘"

Cypher:

MATCH (t1:Tag {normalized_name: $tag_1})
MATCH (t2:Tag {normalized_name: $tag_2})
MATCH path_tag_1 = (r:Restaurant)-[:HAS_TAG]->(t1)
MATCH path_tag_2 = (r)-[:HAS_TAG]->(t2)
RETURN
    r AS restaurant,
    [t1, t2] AS matched_tags,
    [path_tag_1, path_tag_2] AS evidence_paths
ORDER BY
    r.rating DESC,
    r.review_count DESC
LIMIT 10;

필수 파라미터:
- tag_1
- tag_2

예시 파라미터:
- tag_1: 깔끔한
- tag_2: 어른동반적합

기대 결과:
- 조용한카페


============================================================
3. IT 뉴스 쿼리 패턴
============================================================

------------------------------------------------------------
[패턴 07: Topic 기반 뉴스 탐색]
------------------------------------------------------------

사용 예:
- "요즘 AI 관련해서 중요한 뉴스 뭐 있어?"

Cypher:

MATCH (topic:Topic {normalized_name: $topic_name})
MATCH path_topic = (n:NewsArticle)-[:MENTIONS]->(topic)
RETURN
    n AS article,
    topic AS topic,
    [path_topic] AS evidence_paths
ORDER BY
    n.importance_score DESC,
    n.published_at DESC
LIMIT 10;

필수 파라미터:
- topic_name

예시 파라미터:
- topic_name: AI

기대 결과:
- A001
- A002
- A003
- A004


------------------------------------------------------------
[패턴 08: Technology + Event 기반 뉴스 탐색]
------------------------------------------------------------

사용 예:
- "최근 GPT 관련 업데이트 알려줘"

Cypher:

MATCH (tech:Technology {normalized_name: $technology_name})
MATCH (event:Event {normalized_name: $event_name})
MATCH path_tech = (n:NewsArticle)-[:MENTIONS_TECH]->(tech)
MATCH path_event = (n)-[:DESCRIBES_EVENT]->(event)
RETURN
    n AS article,
    tech AS technology,
    event AS event,
    [path_tech, path_event] AS evidence_paths
ORDER BY
    n.published_at DESC,
    n.importance_score DESC
LIMIT 10;

필수 파라미터:
- technology_name
- event_name

예시 파라미터:
- technology_name: GPT
- event_name: 업데이트

기대 결과:
- A001


------------------------------------------------------------
[패턴 09: Company 비교]
------------------------------------------------------------

사용 예:
- "삼성과 애플 최근 기술 경쟁 상황 어때?"

Cypher:

MATCH (c1:Company {normalized_name: $company_1})
MATCH (c2:Company {normalized_name: $company_2})
MATCH (event:Event {normalized_name: $event_name})
MATCH path_c1 = (n:NewsArticle)-[:MENTIONS_COMPANY]->(c1)
MATCH path_c2 = (n)-[:MENTIONS_COMPANY]->(c2)
MATCH path_event = (n)-[:DESCRIBES_EVENT]->(event)
RETURN
    n AS article,
    [c1, c2] AS companies,
    event AS event,
    [path_c1, path_c2, path_event] AS evidence_paths
ORDER BY
    n.published_at DESC,
    n.importance_score DESC
LIMIT 10;

필수 파라미터:
- company_1
- company_2
- event_name

예시 파라미터:
- company_1: 삼성
- company_2: 애플
- event_name: 기술경쟁

기대 결과:
- A003


------------------------------------------------------------
[패턴 10: Topic + Event 기반 트렌드 탐색]
------------------------------------------------------------

사용 예:
- "클라우드 시장에서 요즘 트렌드 뭐야?"

Cypher:

MATCH (topic:Topic {normalized_name: $topic_name})
MATCH (event:Event {normalized_name: $event_name})
MATCH path_topic = (n:NewsArticle)-[:MENTIONS]->(topic)
MATCH path_event = (n)-[:DESCRIBES_EVENT]->(event)
OPTIONAL MATCH path_tech = (n)-[:MENTIONS_TECH]->(tech:Technology)
OPTIONAL MATCH path_company = (n)-[:MENTIONS_COMPANY]->(company:Company)
RETURN
    n AS article,
    topic AS topic,
    event AS event,
    collect(DISTINCT tech) AS technologies,
    collect(DISTINCT company) AS companies,
    [path_topic, path_event] + collect(DISTINCT path_tech) + collect(DISTINCT path_company) AS evidence_paths
ORDER BY
    n.published_at DESC,
    n.importance_score DESC
LIMIT 10;

필수 파라미터:
- topic_name
- event_name

예시 파라미터:
- topic_name: 클라우드
- event_name: 트렌드

기대 결과:
- A002


------------------------------------------------------------
[패턴 11: 보안 사고 탐색]
------------------------------------------------------------

사용 예:
- "보안 관련 사고 최근에 뭐 있었어?"

Cypher:

MATCH (topic:Topic {normalized_name: $topic_name})
MATCH (event:Event {normalized_name: $event_name})
MATCH path_topic = (n:NewsArticle)-[:MENTIONS]->(topic)
MATCH path_event = (n)-[:DESCRIBES_EVENT]->(event)
RETURN
    n AS article,
    topic AS topic,
    event AS event,
    [path_topic, path_event] AS evidence_paths
ORDER BY
    n.published_at DESC,
    n.importance_score DESC
LIMIT 10;

필수 파라미터:
- topic_name
- event_name

예시 파라미터:
- topic_name: 보안
- event_name: 보안사고

기대 결과:
- A005


============================================================
4. Concept 연결 쿼리 패턴
============================================================

------------------------------------------------------------
[패턴 12: 도메인 간 느슨한 연결]
------------------------------------------------------------

사용 예:
- "판교 맛집이랑 판교 IT 뉴스 같이 보고 싶어"

Cypher:

MATCH (concept:Concept {normalized_name: $concept_name})
OPTIONAL MATCH path_restaurant = (r:Restaurant)-[:RELATED_TO]->(concept)
OPTIONAL MATCH path_article = (n:NewsArticle)-[:RELATED_TO]->(concept)
RETURN
    concept AS concept,
    collect(DISTINCT r) AS restaurants,
    collect(DISTINCT n) AS articles,
    collect(DISTINCT path_restaurant) + collect(DISTINCT path_article) AS evidence_paths
LIMIT 10;

필수 파라미터:
- concept_name

예시 파라미터:
- concept_name: 판교

기대 결과:
- Restaurant: 담백한고기집
- NewsArticle: A006

주의:
- Restaurant과 NewsArticle을 직접 연결하지 않는다.
- Concept을 통해서만 느슨하게 연결한다.


============================================================
5. Full-text Search 보조 쿼리 패턴
============================================================

------------------------------------------------------------
[패턴 13: 음식 조건 노드 유사 검색]
------------------------------------------------------------

사용 예:
- "중식", "중국집", "누들", "맵다"

Cypher:

CALL db.index.fulltext.queryNodes(
    "food_condition_text_index",
    $keyword
)
YIELD node, score
RETURN
    node,
    labels(node) AS labels,
    score
ORDER BY score DESC
LIMIT 5;

사용 목적:
- Slot 정규화 실패 시 후보 노드 탐색


------------------------------------------------------------
[패턴 14: 뉴스 조건 노드 유사 검색]
------------------------------------------------------------

사용 예:
- "챗지피티", "오픈AI", "생성AI"

Cypher:

CALL db.index.fulltext.queryNodes(
    "news_condition_text_index",
    $keyword
)
YIELD node, score
RETURN
    node,
    labels(node) AS labels,
    score
ORDER BY score DESC
LIMIT 5;

사용 목적:
- Technology / Topic / Company / Event 후보 탐색


------------------------------------------------------------
[패턴 15: 뉴스 본문 후보 검색]
------------------------------------------------------------

사용 예:
- "AI 인프라 투자"

Cypher:

CALL db.index.fulltext.queryNodes(
    "news_text_index",
    $keyword
)
YIELD node, score
RETURN
    node AS article,
    score
ORDER BY score DESC
LIMIT 10;

사용 목적:
- 관계가 부족한 초기 뉴스 데이터에서 후보 기사 탐색
- 이후 관계 탐색으로 검증 필요

주의:
- Full-text Search 결과를 최종 결과로 바로 쓰지 않는다.
- 관계 기반 검증을 거친다.


============================================================
6. 쿼리 선택 로직
============================================================

입력:
- domain
- intent
- slots

선택 기준:

1. domain = restaurant
   - area + menu + tag 있음
     → 패턴 01

   - menu만 있음
     → 패턴 02

   - menu + excluded_ingredient 있음
     → 패턴 03 또는 03-B

   - menu + required_tag + excluded_tag 있음
     → 패턴 04

   - menu + tag + max_price 있음
     → 패턴 05

   - context 기반 tag 2개 이상 있음
     → 패턴 06


2. domain = it_news
   - topic만 있음
     → 패턴 07

   - technology + event 있음
     → 패턴 08

   - company 2개 + event 있음
     → 패턴 09

   - topic + event 있음
     → 패턴 10 또는 11

   - audience 있음
     → Audience 기반 QueryBuilder에서 topic/technology 가중치 조정


3. domain = mixed
   - concept 있음
     → 패턴 12


4. 정확 매칭 실패
   - 음식 관련
     → 패턴 13

   - 뉴스 조건 관련
     → 패턴 14

   - 뉴스 본문 후보
     → 패턴 15

============================================================
7. 결과 반환 구조
============================================================

모든 쿼리는 다음 구조로 반환한다.

GraphSearchResult:
- query_id
- domain
- result_type
- result_node
- matched_conditions
- excluded_conditions
- evidence_paths
- score
- warning_message

예시 01:
- result_type: Restaurant
- result_node: 조용한카페
- matched_conditions:
  - Menu(카페)
  - Tag(조용한)
- excluded_conditions:
  - Tag(시끄러운)
- evidence_paths:
  - Restaurant -[:SELLS]-> Menu
  - Restaurant -[:HAS_TAG]-> Tag
- warning_message: null


예시 02:
- result_type: NewsArticle
- result_node: A001
- matched_conditions:
  - Technology(GPT)
  - Event(업데이트)
- evidence_paths:
  - NewsArticle -[:MENTIONS_TECH]-> Technology
  - NewsArticle -[:DESCRIBES_EVENT]-> Event
- warning_message: null


예시 03:
- result_type: Mixed
- result_node:
  - Restaurant(담백한고기집)
  - NewsArticle(A006)
- matched_conditions:
  - Concept(판교)
- evidence_paths:
  - Restaurant -[:RELATED_TO]-> Concept
  - NewsArticle -[:RELATED_TO]-> Concept
- warning_message:
  - "맛집과 뉴스는 직접 연결되지 않고 Concept 기준으로 묶였습니다."

============================================================
8. STEP 07 최종 결정
============================================================

이번 단계에서 확정된 쿼리 패턴:

맛집:
1. 지역 + 메뉴 + 태그 추천
2. 메뉴 기반 추천
3. 메뉴 + 부정 재료 제외
4. 메뉴 단위 부정 재료 제외
5. 긍정 태그 + 부정 태그 제외
6. 가격 조건 검색
7. 상황 기반 추천

IT 뉴스:
8. Topic 기반 뉴스 탐색
9. Technology + Event 기반 뉴스 탐색
10. Company 비교
11. Topic + Event 기반 트렌드 탐색
12. 보안 사고 탐색

공통/확장:
13. Concept 기반 도메인 연결
14. 음식 조건 Full-text Search
15. 뉴스 조건 Full-text Search
16. 뉴스 본문 Full-text Search

============================================================
[STEP 07 결론]
============================================================

Cypher 쿼리는 단순 검색문이 아니라 Intent/Slot 기반 Query Template으로 관리한다.

핵심 원칙:
- Relationship 우선
- Property 조건은 보조
- EXCLUDES는 명시적 부정 관계로 유지
- Full-text Search는 보조 후보 탐색
- 모든 결과는 Path 근거와 함께 반환
- LLM은 이 Path를 해석한다

============================================================
[STEP 08] 사용자 발화 → Slot → Query 변환 설계
============================================================

목표:
- 사용자의 자연어 발화를 그래프 DB에서 실행 가능한 Query Template으로 변환하는 과정을 확정한다.
- LLM이 직접 Cypher를 마음대로 생성하지 않게 하고, 정해진 Intent/Slot/Template 구조 안에서만 실행되게 한다.

============================================================
1. 전체 변환 흐름
============================================================

사용자 발화
   ↓
UserQuery 생성
   ↓
Domain 분류
   ↓
Intent 분류
   ↓
Slot 추출
   ↓
Slot 정규화
   ↓
Query Template 선택
   ↓
Query Parameter 생성
   ↓
Neo4j 실행
   ↓
Graph Path 반환
   ↓
LLM Path 해석

============================================================
2. 핵심 원칙
============================================================

1. LLM은 Cypher를 직접 작성하지 않는다.

2. LLM은 다음까지만 수행한다.
   - 도메인 분류 보조
   - Intent 분류 보조
   - Slot 추출 보조
   - Path 해석

3. 실제 Query는 GraphQueryBuilder가 Template 기반으로 생성한다.

4. Slot이 부족하면 Query를 실행하지 않는다.

5. 정확 매칭 실패 시 Full-text Search로 후보 노드를 찾는다.

6. Full-text Search 결과도 바로 최종 검색에 쓰지 않는다.
   - 후보 노드 확인
   - confidence 검증
   - 필요 시 clarification
   - 이후 Relationship 탐색

7. 부정 조건은 반드시 EXCLUDES로 분리한다.

============================================================
3. 변환 데이터 구조
============================================================

------------------------------------------------------------
[UserQuery]
------------------------------------------------------------

필드:
- query_id
- raw_text
- domain
- intent
- status
- created_at

예시:
query_id: Q001
raw_text: "면은 싫은데 중국집 가고 싶어"
domain: restaurant
intent: restaurant_exclusion_search
status: slot_extracted


------------------------------------------------------------
[ExtractedSlot]
------------------------------------------------------------

필드:
- slot_id
- query_id
- slot_type
- node_label
- raw_value
- normalized_value
- confidence
- is_negative
- is_required

예시:
slot_id: S001
query_id: Q001
slot_type: positive_condition
node_label: Menu
raw_value: 중국집
normalized_value: 중국음식
confidence: 0.91
is_negative: false
is_required: true

slot_id: S002
query_id: Q001
slot_type: negative_condition
node_label: Ingredient
raw_value: 면
normalized_value: 면
confidence: 0.96
is_negative: true
is_required: true


------------------------------------------------------------
[QueryBuildResult]
------------------------------------------------------------

필드:
- query_id
- template_id
- cypher_name
- parameters
- expected_result_type
- required_slots
- missing_slots
- fallback_used

예시:
query_id: Q001
template_id: RESTAURANT_MENU_EXCLUDE_INGREDIENT
cypher_name: menu_with_excluded_ingredient
parameters:
  menu_name: 중국음식
  excluded_ingredient: 면
expected_result_type: Restaurant 또는 Menu
required_slots:
  - Menu
  - Ingredient
missing_slots: []
fallback_used: false

============================================================
4. Domain 분류 규칙
============================================================

------------------------------------------------------------
[restaurant]
------------------------------------------------------------

판단 기준:
- 식당, 맛집, 메뉴, 음식, 지역, 분위기, 가격, 배달, 회식, 혼밥 등의 표현 포함

예:
- "강남 맛집 추천해줘"
- "면은 싫은데 중국집 가고 싶어"
- "조용한 카페 알려줘"


------------------------------------------------------------
[it_news]
------------------------------------------------------------

판단 기준:
- 뉴스, 기사, 기술, 기업, 업데이트, 트렌드, 보안, AI, 클라우드, 반도체 등의 표현 포함

예:
- "GPT 업데이트 알려줘"
- "보안 사고 최근에 뭐 있었어?"
- "삼성과 애플 기술 경쟁 상황 어때?"


------------------------------------------------------------
[mixed]
------------------------------------------------------------

판단 기준:
- 맛집과 IT 뉴스가 동시에 등장
- 또는 Concept 기준으로 두 도메인을 묶는 요청

예:
- "판교 맛집이랑 판교 IT 뉴스 같이 보고 싶어"


------------------------------------------------------------
[unknown]
------------------------------------------------------------

판단 기준:
- 도메인 판단 불가
- 조건 부족

예:
- "요즘 뭐가 좋아?"
- "추천해줘"

처리:
- clarification_required

============================================================
5. Intent 분류 규칙
============================================================

------------------------------------------------------------
[맛집 Intent]
------------------------------------------------------------

1. restaurant_recommendation
- 일반 맛집 추천
- 예: "초밥집 추천해줘"

2. restaurant_exclusion_search
- 제외 조건 포함
- 예: "면은 싫은데 중국집 가고 싶어"

3. restaurant_context_recommendation
- 상황 조건 포함
- 예: "부모님 모시고 갈 식당 알려줘"

4. restaurant_price_filter
- 가격 조건 포함
- 예: "1만원 이하 한식집 알려줘"

5. restaurant_area_search
- 지역 조건 중심
- 예: "강남 맛집 알려줘"


------------------------------------------------------------
[IT 뉴스 Intent]
------------------------------------------------------------

1. news_summary
- 뉴스 요약
- 예: "AI 뉴스 요약해줘"

2. news_event_search
- 특정 이벤트 탐색
- 예: "GPT 업데이트 알려줘"

3. news_trend_analysis
- 트렌드 분석
- 예: "클라우드 시장 트렌드 뭐야?"

4. news_comparison
- 비교 요청
- 예: "삼성과 애플 비교해줘"

5. news_audience_filter
- 관점 기반 필터링
- 예: "개발자 입장에서 중요한 뉴스 골라줘"


------------------------------------------------------------
[공통 Intent]
------------------------------------------------------------

1. concept_bridge_search
- Concept 기준 도메인 연결
- 예: "판교 맛집과 판교 IT 뉴스 같이 보고 싶어"

2. clarification_required
- 조건 부족
- 도메인 불명확
- Slot 불충분

3. unsupported_request
- 현재 스키마로 처리 불가

============================================================
6. Slot 추출 규칙
============================================================

------------------------------------------------------------
[맛집 Slot]
------------------------------------------------------------

1. Area
- 예: 강남, 홍대, 을지로, 판교

2. Menu
- 예: 한식, 중국음식, 파스타, 초밥, 고기, 카페

3. Ingredient
- 예: 면, 된장, 오이, 기름진음식

4. Tag
- 예: 조용한, 분위기좋은, 가성비, 혼밥가능, 회식, 배달가능

5. PriceCondition
- 예: 1만원 이하, 2만원 안쪽

6. CapacityCondition
- 예: 6명, 단체 가능

7. Context
- 예: 비, 운동후, 부모님동반, 회사회식


------------------------------------------------------------
[IT 뉴스 Slot]
------------------------------------------------------------

1. Topic
- 예: AI, 클라우드, 보안, 반도체, 스타트업

2. Technology
- 예: GPT, 생성형AI, LLM, GPU, 자율주행

3. Company
- 예: 삼성, 애플, OpenAI, Google, Microsoft

4. Event
- 예: 업데이트, 투자, 규제, 보안사고, 트렌드, 기술경쟁

5. Audience
- 예: 개발자, 창업자, 데이터엔지니어

6. TimeCondition
- 예: 최근, 오늘, 이번 주, 지난달


------------------------------------------------------------
[공통 Slot]
------------------------------------------------------------

1. Concept
- 예: 판교, AI, 스타트업, 개발자

2. NegativeCondition
- 예: 제외, 싫어, 말고, 빼줘, 피하고 싶어

3. ComparisonTarget
- 예: 삼성과 애플, 오픈소스AI와 상용AI

============================================================
7. 부정 조건 변환 규칙
============================================================

부정 표현:
- 싫어
- 말고
- 제외
- 빼줘
- 안 들어간
- 피하고 싶어
- 원하지 않아

변환 방식:
- negative_condition Slot 생성
- UserIntent -[:EXCLUDES]-> 대상 노드 생성

예시 01:
발화:
- "면은 싫은데 중국집 가고 싶어"

Slot:
- Menu: 중국음식
- Ingredient: 면
- is_negative: true

Graph:
- UserIntent -[:PREFERS]-> Menu(중국음식)
- UserIntent -[:EXCLUDES {strength:"hard"}]-> Ingredient(면)


예시 02:
발화:
- "시끄러운 곳 말고 조용한 카페 알려줘"

Slot:
- Menu: 카페
- Tag: 조용한
- Tag: 시끄러운 / negative

Graph:
- UserIntent -[:PREFERS]-> Menu(카페)
- UserIntent -[:REQUIRES]-> Tag(조용한)
- UserIntent -[:EXCLUDES {strength:"hard"}]-> Tag(시끄러운)

============================================================
8. Slot 정규화 규칙
============================================================

------------------------------------------------------------
[정확 매칭]
------------------------------------------------------------

예:
- 강남 → Area(강남)
- GPT → Technology(GPT)
- 삼성 → Company(삼성)


------------------------------------------------------------
[동의어 정규화]
------------------------------------------------------------

맛집:
- 중국집 → 중국음식
- 중식 → 중국음식
- 이탈리안 → 이탈리안
- 혼밥 → 혼밥가능
- 조용한 곳 → 조용한

IT 뉴스:
- 챗지피티 → GPT
- ChatGPT → GPT
- 생성AI → 생성형AI
- 클라우드 시장 → 클라우드
- 보안 사고 → 보안사고


------------------------------------------------------------
[Full-text Search fallback]
------------------------------------------------------------

조건:
- normalized_value로 정확 매칭 실패
- confidence 낮음
- 유사 표현 가능성 있음

처리:
1. Full-text Index 검색
2. 후보 노드 반환
3. score 기준 후보 선택
4. score 낮거나 후보 다수이면 clarification

============================================================
9. Query Template 선택 규칙
============================================================

------------------------------------------------------------
[맛집]
------------------------------------------------------------

1. Area + Menu + Tag
→ RESTAURANT_AREA_MENU_TAG

2. Menu only
→ RESTAURANT_MENU_ONLY

3. Menu + Negative Ingredient
→ RESTAURANT_MENU_EXCLUDE_INGREDIENT

4. Menu + Required Tag + Negative Tag
→ RESTAURANT_MENU_REQUIRED_TAG_EXCLUDE_TAG

5. Menu + Tag + PriceCondition
→ RESTAURANT_MENU_TAG_PRICE

6. Context + Tags
→ RESTAURANT_CONTEXT_TAGS


------------------------------------------------------------
[IT 뉴스]
------------------------------------------------------------

1. Topic only
→ NEWS_TOPIC_SEARCH

2. Technology + Event
→ NEWS_TECH_EVENT_SEARCH

3. Company + Company + Event
→ NEWS_COMPANY_COMPARISON

4. Topic + Event
→ NEWS_TOPIC_EVENT_SEARCH

5. Audience + Topic
→ NEWS_AUDIENCE_FILTER


------------------------------------------------------------
[Mixed]
------------------------------------------------------------

1. Concept
→ CONCEPT_BRIDGE_SEARCH

============================================================
10. Clarification 조건
============================================================

다음 경우에는 검색하지 않는다.

1. 도메인이 unknown

2. Intent가 불명확함

3. 필수 Slot이 부족함

4. 부정 조건 대상이 불명확함
   - 예: "그거 빼고 추천해줘"

5. Full-text 후보가 여러 개이고 score 차이가 작음

6. 검색 범위가 너무 넓음
   - 예: "좋은 거 추천해줘"

7. mixed 요청인데 Concept이 추출되지 않음

Clarification 예시:
- "맛집 추천인지 IT 뉴스 추천인지 먼저 정해야 합니다."
- "어떤 지역이나 음식 종류를 기준으로 추천할까요?"
- "제외하고 싶은 대상이 메뉴인지 재료인지 분위기인지 확인이 필요합니다."

============================================================
11. 예시 변환
============================================================

------------------------------------------------------------
[예시 01]
------------------------------------------------------------

입력:
- "면은 싫은데 중국집 가고 싶어"

결과:
domain:
- restaurant

intent:
- restaurant_exclusion_search

slots:
- Menu: 중국음식
- Ingredient: 면 / negative / hard

template:
- RESTAURANT_MENU_EXCLUDE_INGREDIENT

parameters:
- menu_name: 중국음식
- excluded_ingredient: 면


------------------------------------------------------------
[예시 02]
------------------------------------------------------------

입력:
- "최근 GPT 관련 업데이트 알려줘"

결과:
domain:
- it_news

intent:
- news_event_search

slots:
- Technology: GPT
- Event: 업데이트
- TimeCondition: 최근

template:
- NEWS_TECH_EVENT_SEARCH

parameters:
- technology_name: GPT
- event_name: 업데이트


------------------------------------------------------------
[예시 03]
------------------------------------------------------------

입력:
- "판교 맛집이랑 판교 IT 뉴스 같이 보고 싶어"

결과:
domain:
- mixed

intent:
- concept_bridge_search

slots:
- Concept: 판교

template:
- CONCEPT_BRIDGE_SEARCH

parameters:
- concept_name: 판교

============================================================
12. STEP 08 최종 결정
============================================================

사용자 발화 변환 구조는 다음으로 확정한다.

1. UserQuery 생성
2. DomainClassifier 실행
3. IntentClassifier 실행
4. SlotExtractor 실행
5. SlotNormalizer 실행
6. GraphQueryBuilder 실행
7. Query Template 선택
8. Query Parameter 생성
9. Neo4j 실행
10. Path 기반 결과 반환
11. LLM Path 해석

핵심 결정:
- LLM은 Cypher를 직접 생성하지 않는다.
- Query는 Template 기반으로만 생성한다.
- 부정 조건은 EXCLUDES로 분리한다.
- 정확 매칭 실패 시 Full-text Search를 보조로 사용한다.
- Slot 부족 시 검색하지 않고 Clarification으로 보낸다.

============================================================
[STEP 08 결론]
============================================================

이 단계에서 사용자 발화가 그래프 DB 쿼리로 변환되는 전체 기준이 확정되었다.

============================================================
[STEP 09] 테스트 시나리오별 검증 기준 작성
============================================================

목표:
- 지금까지 정의한 그래프 DB 스키마, 샘플 데이터, Cypher Query Template이 실제로 동작하는지 검증한다.
- 맛집 / IT 뉴스 / mixed Concept 연결 / 부정 조건 / Full-text fallback / Clarification 조건을 테스트한다.

============================================================
1. 테스트 검증 원칙
============================================================

1. 테스트는 사용자 발화 기준으로 작성한다.

2. 각 테스트는 다음 항목을 반드시 가진다.
   - 입력 발화
   - 기대 Domain
   - 기대 Intent
   - 기대 Slot
   - 선택되어야 하는 Query Template
   - 기대 결과
   - 검증해야 하는 Graph Path
   - 실패 조건

3. 결과 노드만 맞으면 통과가 아니다.
   - Path 근거가 함께 반환되어야 한다.

4. 부정 조건은 EXCLUDES 관계와 NOT EXISTS 탐색이 함께 검증되어야 한다.

5. Full-text Search는 정확 매칭 실패 시에만 fallback으로 사용되어야 한다.

6. Slot이 부족한 발화는 검색하지 않고 clarification_required가 되어야 한다.

============================================================
2. 맛집 테스트 시나리오
============================================================

------------------------------------------------------------
[TEST-R-01] 지역 + 메뉴 + 태그 추천
------------------------------------------------------------

입력 발화:
- "강남에서 분위기 좋은 이탈리안 레스토랑 추천해줘"

기대 Domain:
- restaurant

기대 Intent:
- restaurant_recommendation

기대 Slot:
- Area: 강남
- Menu: 이탈리안
- Tag: 분위기좋은

선택 Query Template:
- RESTAURANT_AREA_MENU_TAG

기대 결과:
- Restaurant: 강남파스타

검증 Graph Path:
- Restaurant(강남파스타) -[:LOCATED_IN]-> Area(강남)
- Restaurant(강남파스타) -[:SELLS]-> Menu(이탈리안)
- Restaurant(강남파스타) -[:HAS_TAG]-> Tag(분위기좋은)

실패 조건:
- 강남이 Property 조건으로만 검색됨
- Area 관계가 evidence_paths에 없음
- 이탈리안 또는 분위기좋은 Path가 누락됨


------------------------------------------------------------
[TEST-R-02] 메뉴 기반 추천
------------------------------------------------------------

입력 발화:
- "초밥집 추천해줘"

기대 Domain:
- restaurant

기대 Intent:
- restaurant_recommendation

기대 Slot:
- Menu: 초밥

선택 Query Template:
- RESTAURANT_MENU_ONLY

기대 결과:
- Restaurant: 홍대초밥

검증 Graph Path:
- Restaurant(홍대초밥) -[:SELLS]-> Menu(초밥)

실패 조건:
- Menu 관계 없이 이름 검색만으로 반환됨
- evidence_paths가 비어 있음


------------------------------------------------------------
[TEST-R-03] 메뉴 + 부정 재료 제외
------------------------------------------------------------

입력 발화:
- "면은 싫은데 중국집 가고 싶어"

기대 Domain:
- restaurant

기대 Intent:
- restaurant_exclusion_search

기대 Slot:
- Menu: 중국음식
- Ingredient: 면
- NegativeCondition: hard

선택 Query Template:
- RESTAURANT_MENU_EXCLUDE_INGREDIENT
- 또는 메뉴 단위 요청이면 RESTAURANT_MENU_EXCLUDE_INGREDIENT_MENU_LEVEL

기대 결과:
- 식당 단위 엄격 검색:
  - 홍콩반점은 짜장면/짬뽕이 면을 포함하므로 제외될 수 있음
- 메뉴 단위 검색:
  - 면 없는 메뉴만 반환
  - 샘플 데이터상 면 없는 중국음식 메뉴가 없으면 빈 결과 허용

검증 Graph Path:
- UserIntent(Q001) -[:PREFERS]-> Menu(중국음식)
- UserIntent(Q001) -[:EXCLUDES {strength:"hard"}]-> Ingredient(면)
- Menu(짜장면) -[:CONTAINS]-> Ingredient(면)
- Menu(짬뽕) -[:CONTAINS]-> Ingredient(면)

실패 조건:
- 면 포함 메뉴가 추천됨
- EXCLUDES 관계가 생성되지 않음
- NOT EXISTS 검증 없이 추천됨


------------------------------------------------------------
[TEST-R-04] 긍정 태그 + 부정 태그 제외
------------------------------------------------------------

입력 발화:
- "시끄러운 곳 말고 조용한 카페 알려줘"

기대 Domain:
- restaurant

기대 Intent:
- restaurant_exclusion_search

기대 Slot:
- Menu: 카페
- Tag: 조용한
- Negative Tag: 시끄러운
- NegativeCondition: hard

선택 Query Template:
- RESTAURANT_MENU_REQUIRED_TAG_EXCLUDE_TAG

기대 결과:
- Restaurant: 조용한카페

검증 Graph Path:
- Restaurant(조용한카페) -[:SELLS]-> Menu(카페)
- Restaurant(조용한카페) -[:HAS_TAG]-> Tag(조용한)
- UserIntent -[:EXCLUDES {strength:"hard"}]-> Tag(시끄러운)

실패 조건:
- 시끄러운 Tag가 있는 Restaurant이 반환됨
- 조용한 Tag Path가 누락됨
- EXCLUDES 관계가 누락됨


------------------------------------------------------------
[TEST-R-05] 가격 조건 검색
------------------------------------------------------------

입력 발화:
- "혼자 가기 편한 한식집 중에 가격 1만원 이하로 알려줘"

기대 Domain:
- restaurant

기대 Intent:
- restaurant_price_filter

기대 Slot:
- Menu: 한식
- Tag: 혼밥가능
- PriceCondition: max_price = 10000

선택 Query Template:
- RESTAURANT_MENU_TAG_PRICE

기대 결과:
- 샘플 데이터 기준 결과 없음 가능
- 이유:
  - 건강한한식은 한식이지만 avg_price = 12000
  - 홍대초밥은 혼밥가능이지만 한식이 아님

검증 Graph Path:
- Restaurant -[:SELLS]-> Menu(한식)
- Restaurant -[:HAS_TAG]-> Tag(혼밥가능)
- Restaurant.avg_price <= 10000

실패 조건:
- 가격 조건을 무시하고 건강한한식이 반환됨
- 관계 조건 없이 avg_price만으로 검색됨


------------------------------------------------------------
[TEST-R-06] 상황 기반 추천
------------------------------------------------------------

입력 발화:
- "부모님 모시고 갈 수 있는 깔끔한 식당 알려줘"

기대 Domain:
- restaurant

기대 Intent:
- restaurant_context_recommendation

기대 Slot:
- Context: 부모님동반
- Tag: 깔끔한
- Tag: 어른동반적합

선택 Query Template:
- RESTAURANT_CONTEXT_TAGS

기대 결과:
- Restaurant: 조용한카페

검증 Graph Path:
- Restaurant(조용한카페) -[:HAS_TAG]-> Tag(깔끔한)
- Restaurant(조용한카페) -[:HAS_TAG]-> Tag(어른동반적합)

실패 조건:
- Context만 보고 임의 추천됨
- Tag 근거 없이 추천됨


------------------------------------------------------------
[TEST-R-07] 야간영업 추천
------------------------------------------------------------

입력 발화:
- "늦은 밤에도 하는 식당 있어?"

기대 Domain:
- restaurant

기대 Intent:
- restaurant_context_recommendation

기대 Slot:
- Tag: 야간영업

선택 Query Template:
- RESTAURANT_CONTEXT_TAGS 또는 RESTAURANT_TAG_ONLY

기대 결과:
- Restaurant: 야간분식

검증 Graph Path:
- Restaurant(야간분식) -[:HAS_TAG]-> Tag(야간영업)

실패 조건:
- 야간영업 Tag 없이 반환됨

============================================================
3. IT 뉴스 테스트 시나리오
============================================================

------------------------------------------------------------
[TEST-N-01] Topic 기반 뉴스 탐색
------------------------------------------------------------

입력 발화:
- "요즘 AI 관련해서 중요한 뉴스 뭐 있어?"

기대 Domain:
- it_news

기대 Intent:
- news_summary

기대 Slot:
- Topic: AI
- TimeCondition: 최근

선택 Query Template:
- NEWS_TOPIC_SEARCH

기대 결과:
- A001
- A002
- A003
- A004

정렬 기대:
- importance_score DESC
- published_at DESC

검증 Graph Path:
- NewsArticle -[:MENTIONS]-> Topic(AI)

실패 조건:
- Topic 관계 없이 title 검색만 사용됨
- importance_score 정렬이 적용되지 않음


------------------------------------------------------------
[TEST-N-02] Technology + Event 탐색
------------------------------------------------------------

입력 발화:
- "최근 GPT 관련 업데이트 알려줘"

기대 Domain:
- it_news

기대 Intent:
- news_event_search

기대 Slot:
- Technology: GPT
- Event: 업데이트
- TimeCondition: 최근

선택 Query Template:
- NEWS_TECH_EVENT_SEARCH

기대 결과:
- NewsArticle: A001

검증 Graph Path:
- NewsArticle(A001) -[:MENTIONS_TECH]-> Technology(GPT)
- NewsArticle(A001) -[:DESCRIBES_EVENT]-> Event(업데이트)

실패 조건:
- GPT만 보고 업데이트 아닌 뉴스가 반환됨
- Event Path가 누락됨


------------------------------------------------------------
[TEST-N-03] Company 비교
------------------------------------------------------------

입력 발화:
- "삼성과 애플 최근 기술 경쟁 상황 어때?"

기대 Domain:
- it_news

기대 Intent:
- news_comparison

기대 Slot:
- Company: 삼성
- Company: 애플
- Event: 기술경쟁

선택 Query Template:
- NEWS_COMPANY_COMPARISON

기대 결과:
- NewsArticle: A003

검증 Graph Path:
- NewsArticle(A003) -[:MENTIONS_COMPANY]-> Company(삼성)
- NewsArticle(A003) -[:MENTIONS_COMPANY]-> Company(애플)
- NewsArticle(A003) -[:DESCRIBES_EVENT]-> Event(기술경쟁)

실패 조건:
- 삼성 또는 애플 중 하나만 포함된 기사 반환
- 비교 대상이 하나만 추출됨


------------------------------------------------------------
[TEST-N-04] Topic + Event 트렌드 탐색
------------------------------------------------------------

입력 발화:
- "클라우드 시장에서 요즘 트렌드 뭐야?"

기대 Domain:
- it_news

기대 Intent:
- news_trend_analysis

기대 Slot:
- Topic: 클라우드
- Event: 트렌드

선택 Query Template:
- NEWS_TOPIC_EVENT_SEARCH

기대 결과:
- NewsArticle: A002

검증 Graph Path:
- NewsArticle(A002) -[:MENTIONS]-> Topic(클라우드)
- NewsArticle(A002) -[:DESCRIBES_EVENT]-> Event(트렌드)

실패 조건:
- 클라우드 Topic만 보고 트렌드 Event 없는 기사 반환


------------------------------------------------------------
[TEST-N-05] 보안 사고 탐색
------------------------------------------------------------

입력 발화:
- "보안 관련 사고 최근에 뭐 있었어?"

기대 Domain:
- it_news

기대 Intent:
- news_event_search

기대 Slot:
- Topic: 보안
- Event: 보안사고

선택 Query Template:
- NEWS_TOPIC_EVENT_SEARCH

기대 결과:
- NewsArticle: A005

검증 Graph Path:
- NewsArticle(A005) -[:MENTIONS]-> Topic(보안)
- NewsArticle(A005) -[:DESCRIBES_EVENT]-> Event(보안사고)

실패 조건:
- 보안 Topic만 있고 보안사고 Event 없는 기사 반환


------------------------------------------------------------
[TEST-N-06] Audience 기반 필터링
------------------------------------------------------------

입력 발화:
- "개발자 입장에서 중요한 IT 뉴스만 골라줘"

기대 Domain:
- it_news

기대 Intent:
- news_audience_filter

기대 Slot:
- Audience: 개발자
- Topic: IT

선택 Query Template:
- NEWS_AUDIENCE_FILTER

기대 결과:
- 개발자와 관련 높은 Technology/Topic 기사 우선
- 후보 예:
  - A001: GPT, LLM
  - A002: 클라우드인프라, GPU
  - A005: 보안

검증 Graph Path:
- UserIntent -[:FOR_AUDIENCE]-> Audience(개발자)
- NewsArticle -[:MENTIONS]-> Topic 또는 NewsArticle -[:MENTIONS_TECH]-> Technology

실패 조건:
- Audience 조건이 무시됨
- IT 전체 뉴스가 무작위로 반환됨

============================================================
4. Mixed / Concept 테스트 시나리오
============================================================

------------------------------------------------------------
[TEST-M-01] Concept 기반 도메인 연결
------------------------------------------------------------

입력 발화:
- "판교 맛집이랑 판교 IT 뉴스 같이 보고 싶어"

기대 Domain:
- mixed

기대 Intent:
- concept_bridge_search

기대 Slot:
- Concept: 판교

선택 Query Template:
- CONCEPT_BRIDGE_SEARCH

기대 결과:
- Restaurant: 담백한고기집
- NewsArticle: A006

검증 Graph Path:
- Restaurant(담백한고기집) -[:RELATED_TO]-> Concept(판교)
- NewsArticle(A006) -[:RELATED_TO]-> Concept(판교)

실패 조건:
- Restaurant과 NewsArticle이 직접 연결됨
- Concept 없이 두 도메인을 억지 연결함

============================================================
5. Full-text Search fallback 테스트
============================================================

------------------------------------------------------------
[TEST-F-01] 음식 조건 유사어 fallback
------------------------------------------------------------

입력 발화:
- "중식 먹고 싶어"

기대 처리:
1. normalized_name = 중국음식으로 정규화 시도
2. 정확 매칭 성공 시 Full-text 사용 안 함
3. 정확 매칭 실패 시 food_condition_text_index 사용

기대 결과:
- Menu(중국음식) 후보 선택

실패 조건:
- 정확 매칭 가능한데 Full-text를 먼저 사용함
- Full-text 결과를 관계 검증 없이 최종 반환함


------------------------------------------------------------
[TEST-F-02] 뉴스 기술 유사어 fallback
------------------------------------------------------------

입력 발화:
- "챗지피티 업데이트 알려줘"

기대 처리:
1. 챗지피티 → GPT 정규화 시도
2. 실패 시 news_condition_text_index 사용
3. Technology(GPT) 후보 선택
4. NEWS_TECH_EVENT_SEARCH 실행

기대 결과:
- A001

실패 조건:
- Full-text 결과만으로 기사 반환
- Technology/Event 관계 검증 없이 답변 생성


------------------------------------------------------------
[TEST-F-03] 뉴스 본문 fallback
------------------------------------------------------------

입력 발화:
- "AI 인프라 투자 뉴스 있어?"

기대 처리:
1. Topic(AI), Event(투자) 추출
2. 관계 탐색 우선
3. 관계 탐색 결과 부족 시 news_text_index 보조 사용
4. 후보 기사에 대해 Topic/Event 관계 검증

기대 결과:
- A002

실패 조건:
- 본문 Full-text 결과를 바로 최종 결과로 반환
- evidence_paths 없이 응답

============================================================
6. Clarification 테스트 시나리오
============================================================

------------------------------------------------------------
[TEST-C-01] 도메인 불명확
------------------------------------------------------------

입력 발화:
- "요즘 뭐가 좋아?"

기대 결과:
- clarification_required

기대 질문:
- "맛집 추천을 원하는지 IT 뉴스 추천을 원하는지 먼저 정해야 합니다."

실패 조건:
- 임의로 맛집 또는 IT 뉴스로 분류함


------------------------------------------------------------
[TEST-C-02] 맛집 조건 부족
------------------------------------------------------------

입력 발화:
- "추천해줘"

기대 결과:
- clarification_required

기대 질문:
- "지역, 음식 종류, 분위기 중 하나는 필요합니다."

실패 조건:
- 무작위 Restaurant 반환


------------------------------------------------------------
[TEST-C-03] 부정 대상 불명확
------------------------------------------------------------

입력 발화:
- "그거 빼고 추천해줘"

기대 결과:
- clarification_required

기대 질문:
- "제외하려는 대상이 메뉴, 재료, 분위기 중 무엇인지 확인이 필요합니다."

실패 조건:
- 이전 문맥 없이 EXCLUDES 생성


------------------------------------------------------------
[TEST-C-04] Mixed Concept 부족
------------------------------------------------------------

입력 발화:
- "맛집이랑 뉴스 같이 보여줘"

기대 결과:
- clarification_required

기대 질문:
- "어떤 공통 기준으로 묶을지 필요합니다. 예: 판교, AI, 스타트업"

실패 조건:
- 모든 Restaurant과 NewsArticle을 무작위 반환

============================================================
7. 테스트 통과 기준
============================================================

각 테스트는 다음을 만족해야 통과한다.

1. Domain이 기대값과 일치한다.

2. Intent가 기대값과 일치한다.

3. 필수 Slot이 추출된다.

4. 부정 조건은 is_negative=true로 분리된다.

5. Query Template이 올바르게 선택된다.

6. Neo4j 결과가 기대 결과와 일치한다.

7. evidence_paths가 비어 있지 않다.

8. Relationship 기반 Path가 포함된다.

9. EXCLUDES 조건은 결과에서 실제 제외 효과를 가진다.

10. Full-text Search는 fallback으로만 사용된다.

11. Clarification 대상 발화는 Query를 실행하지 않는다.

12. LLM 설명은 evidence_paths 안의 내용만 사용한다.

============================================================
8. 테스트 우선순위
============================================================

[1순위]
- TEST-R-03: 메뉴 + 부정 재료 제외
- TEST-R-04: 긍정 태그 + 부정 태그 제외
- TEST-N-02: Technology + Event 탐색
- TEST-M-01: Concept 기반 도메인 연결

이유:
- KAG 구조의 핵심 검증 대상
- EXCLUDES, Relationship 탐색, Path 해석이 모두 포함됨


[2순위]
- TEST-R-01
- TEST-R-02
- TEST-N-01
- TEST-N-03
- TEST-N-04

이유:
- 기본 추천/뉴스 검색 품질 검증


[3순위]
- Full-text fallback 테스트
- Clarification 테스트

이유:
- 안정성 및 예외 처리 검증

============================================================
9. STEP 09 최종 결정
============================================================

테스트는 단순 결과 검증이 아니라 다음 4가지를 함께 검증한다.

1. 자연어 발화가 Slot으로 잘 분해되는가
2. Slot이 올바른 Query Template으로 연결되는가
3. Query 결과가 Relationship Path 근거를 포함하는가
4. LLM이 Path 기반으로만 설명할 수 있는 구조인가

============================================================
[STEP 09 결론]
============================================================

테스트 시나리오별 검증 기준이 확정되었다.

============================================================
[STEP 10] 최종 구현용 설계서 통합
============================================================

목표:
- STEP 01 ~ STEP 09에서 확정한 내용을 구현 직전 기준으로 통합한다.
- Neo4j 그래프 DB 구현, 샘플 데이터 적재, Query Template, 테스트 검증까지 이어지는 기준 문서로 사용한다.

============================================================
1. 최종 구현 방향
============================================================

최종 선택:
- 맛집 / IT 뉴스 도메인을 하나의 Neo4j DB 안에 구성한다.
- 단, 도메인별 핵심 노드와 관계는 분리한다.
- Restaurant과 NewsArticle은 직접 연결하지 않는다.
- 도메인 간 느슨한 연결은 Concept 노드로 처리한다.
- 검색은 Property보다 Relationship 탐색을 우선한다.
- LLM은 Cypher를 직접 생성하지 않는다.
- LLM은 Neo4j에서 반환된 Path를 해석하는 역할만 수행한다.

최종 전략:
- [방안 03-A: Relationship 중심 혼합 전략 + EXCLUDES 구체화 + Full-text 보조 검색]

============================================================
2. 전체 처리 흐름
============================================================

사용자 발화
→ UserQuery 생성
→ DomainClassifier
→ IntentClassifier
→ SlotExtractor
→ SlotNormalizer
→ GraphQueryBuilder
→ Query Template 선택
→ Neo4j 실행
→ Graph Path 반환
→ LLM Path Interpreter
→ 최종 응답 생성

============================================================
3. 공통 노드
============================================================

[UserIntent]
- query_id
- raw_text
- domain
- intent
- status
- created_at

[Concept]
- concept_id
- name
- normalized_name
- concept_type

[Audience]
- audience_id
- name
- normalized_name
- audience_type

============================================================
4. 맛집 도메인 노드
============================================================

[Restaurant]
- restaurant_id
- name
- address
- phone
- url
- rating
- review_count
- avg_price
- min_price
- max_price
- latitude
- longitude
- description
- is_active
- created_at
- updated_at

[Area]
- area_id
- name
- parent_area
- level

[Menu]
- menu_id
- name
- normalized_name
- menu_type
- price

[Ingredient]
- ingredient_id
- name
- normalized_name

[Tag]
- tag_id
- name
- normalized_name
- tag_type

[Context]
- context_id
- name
- context_type

[PriceCondition]
- condition_id
- operator
- value
- currency

[CapacityCondition]
- condition_id
- min_capacity
- max_capacity

============================================================
5. IT 뉴스 도메인 노드
============================================================

[NewsArticle]
- article_id
- title
- content
- summary
- published_at
- url
- source
- author
- language
- importance_score
- reliability_score
- created_at
- updated_at

[Topic]
- topic_id
- name
- normalized_name
- topic_type

[Technology]
- technology_id
- name
- normalized_name
- technology_type

[Company]
- company_id
- name
- normalized_name
- company_type
- country

[Event]
- event_id
- name
- normalized_name
- event_type

============================================================
6. 핵심 관계
============================================================

[맛집 관계]
- Restaurant -[:LOCATED_IN]-> Area
- Restaurant -[:HAS_TAG]-> Tag
- Restaurant -[:SELLS]-> Menu
- Menu -[:CONTAINS]-> Ingredient
- UserIntent -[:TARGET_AREA]-> Area
- UserIntent -[:PREFERS]-> Menu
- UserIntent -[:REQUIRES]-> Tag
- UserIntent -[:EXCLUDES]-> Menu / Ingredient / Tag
- UserIntent -[:MAX_PRICE]-> PriceCondition
- UserIntent -[:MIN_CAPACITY]-> CapacityCondition
- UserIntent -[:HAS_CONTEXT]-> Context
- Restaurant -[:RELATED_TO]-> Concept

[IT 뉴스 관계]
- NewsArticle -[:MENTIONS]-> Topic
- NewsArticle -[:MENTIONS_TECH]-> Technology
- NewsArticle -[:MENTIONS_COMPANY]-> Company
- NewsArticle -[:DESCRIBES_EVENT]-> Event
- Topic -[:RELATED_TO]-> Technology
- Company -[:RELATED_TO]-> Technology
- UserIntent -[:INTERESTED_IN]-> Topic / Technology / Concept
- UserIntent -[:FOCUSES_ON]-> Company
- UserIntent -[:REQUESTS]-> Event
- UserIntent -[:FOR_AUDIENCE]-> Audience
- NewsArticle -[:RELATED_TO]-> Concept

============================================================
7. EXCLUDES 최종 규칙
============================================================

EXCLUDES 관계 대상:
- Ingredient
- Menu
- Tag
- Concept

EXCLUDES 관계 속성:
- reason_text
- exclude_type
- strength
- created_at

strength:
- hard: 절대 제외
- soft: 가능하면 제외

기본 규칙:
- "싫어", "빼줘", "제외", "말고", "안 들어간"은 hard로 처리한다.
- "피하고 싶어", "별로"는 soft 또는 clarification으로 처리한다.
- 부정 조건은 검색 조건과 반드시 분리한다.
- EXCLUDES 관계는 결과 설명에도 사용한다.

============================================================
8. Neo4j 제약조건 / 인덱스 전략
============================================================

최종 선택:
- 혼합 전략

생성 대상:
- 핵심 노드는 UNIQUE CONSTRAINT 생성
- normalized_name 기반 노드는 normalized_name에 UNIQUE 적용
- Restaurant, NewsArticle은 ID와 URL 중심으로 중복 방지
- 시작 노드와 정렬 필드에만 Index 생성
- Full-text Index는 보조 검색용으로만 사용

Full-text Index:
- restaurant_text_index
- food_condition_text_index
- news_text_index
- news_condition_text_index

주의:
- Full-text Search는 최종 결과 생성용이 아니다.
- 정확 매칭 실패 시 후보 노드 탐색용이다.
- 후보 노드를 찾은 뒤 다시 Relationship 탐색으로 검증한다.

============================================================
9. Query Template 목록
============================================================

[맛집]
1. RESTAURANT_AREA_MENU_TAG
2. RESTAURANT_MENU_ONLY
3. RESTAURANT_MENU_EXCLUDE_INGREDIENT
4. RESTAURANT_MENU_EXCLUDE_INGREDIENT_MENU_LEVEL
5. RESTAURANT_MENU_REQUIRED_TAG_EXCLUDE_TAG
6. RESTAURANT_MENU_TAG_PRICE
7. RESTAURANT_CONTEXT_TAGS
8. RESTAURANT_TAG_ONLY

[IT 뉴스]
1. NEWS_TOPIC_SEARCH
2. NEWS_TECH_EVENT_SEARCH
3. NEWS_COMPANY_COMPARISON
4. NEWS_TOPIC_EVENT_SEARCH
5. NEWS_AUDIENCE_FILTER

[공통 / 확장]
1. CONCEPT_BRIDGE_SEARCH
2. FOOD_CONDITION_FULLTEXT_SEARCH
3. NEWS_CONDITION_FULLTEXT_SEARCH
4. NEWS_TEXT_FULLTEXT_SEARCH

============================================================
10. 샘플 데이터 규모
============================================================

[맛집]
- Restaurant: 8개
- Area: 6개
- Menu: 12개
- Ingredient: 5개
- Tag: 14개

[IT 뉴스]
- NewsArticle: 6개
- Topic: 7개
- Technology: 6개
- Company: 6개
- Event: 7개
- Audience: 3개

[공통]
- Concept: 5개
- UserIntent: 5개

목적:
- 대량 데이터 구축이 아니라 쿼리 검증용 최소 그래프 구축

============================================================
11. 테스트 우선순위
============================================================

[1순위]
- TEST-R-03: 메뉴 + 부정 재료 제외
- TEST-R-04: 긍정 태그 + 부정 태그 제외
- TEST-N-02: Technology + Event 탐색
- TEST-M-01: Concept 기반 도메인 연결

[2순위]
- TEST-R-01: 지역 + 메뉴 + 태그 추천
- TEST-R-02: 메뉴 기반 추천
- TEST-N-01: Topic 기반 뉴스 탐색
- TEST-N-03: Company 비교
- TEST-N-04: Topic + Event 트렌드 탐색

[3순위]
- Full-text fallback 테스트
- Clarification 테스트

============================================================
12. 구현 순서
============================================================

1. Neo4j 실행 환경 준비
2. Constraint / Index 생성
3. Full-text Index 생성
4. 맛집 샘플 노드 생성
5. 맛집 샘플 관계 생성
6. IT 뉴스 샘플 노드 생성
7. IT 뉴스 샘플 관계 생성
8. Concept 연결 관계 생성
9. UserIntent 샘플 생성
10. Query Template 작성
11. QueryBuilder 매핑 작성
12. 테스트 시나리오 실행
13. evidence_paths 반환 구조 검증
14. LLM Path Interpreter 설계 연결

============================================================
13. 구현 시 금지 규칙
============================================================

1. LLM이 Cypher를 직접 생성하게 하지 않는다.

2. Restaurant과 NewsArticle을 직접 연결하지 않는다.

3. 사용자 발화 raw_text를 바로 검색 조건으로 사용하지 않는다.

4. 관계로 표현 가능한 값을 Restaurant 또는 NewsArticle Property에만 저장하지 않는다.

5. Full-text Search를 메인 검색으로 사용하지 않는다.

6. evidence_paths 없이 결과만 반환하지 않는다.

7. 부정 조건을 단순 텍스트 필터로만 처리하지 않는다.

8. Slot이 부족한 상태에서 임의 검색하지 않는다.

9. Clarification 대상 발화를 억지로 추천 결과로 바꾸지 않는다.

10. LLM이 없는 관계나 없는 근거를 설명하지 않는다.

============================================================
14. 최종 아키텍처 결론
============================================================

이 그래프 DB는 단순 검색 DB가 아니다.

핵심 목적:
- 사용자 발화를 구조화한다.
- Slot을 그래프 조건으로 변환한다.
- 관계 기반으로 후보를 탐색한다.
- Path를 근거로 반환한다.
- LLM은 Path를 해석해서 설명한다.

최종 구조:
UserQuery
→ UserIntent
→ Slot
→ Graph Query Template
→ Neo4j Relationship Search
→ Evidence Path
→ LLM Path Explanation

============================================================
15. 다음 구현 단계
============================================================

다음부터는 실제 구현 설계로 들어간다.

권장 순서:

[STEP 11]
- Neo4j Constraint / Index 생성 Cypher 작성

[STEP 12]
- 샘플 데이터 적재 Cypher 작성

[STEP 13]
- Query Template Cypher 파일 구조 설계

[STEP 14]
- Python GraphQueryBuilder 구조 설계

[STEP 15]
- 테스트 코드 구조 설계

============================================================
[STEP 10 결론]
============================================================

STEP 01 ~ STEP 09의 설계는 구현 가능한 그래프 DB 기준으로 통합 완료한다.

최종 선택:
- 방안 03-A
- Relationship 중심 혼합 전략
- EXCLUDES 구체화
- Full-text Search 보조 적용
- Concept 기반 도메인 느슨한 연결
- Path 기반 LLM 해석 구조

============================================================
[STEP 10 보완] 구현 시 금지 규칙 및 코드 설계 규칙 추가
============================================================

기존 금지 규칙은 유지한다.

아래 규칙을 추가한다.

============================================================
1. 하드 코딩 금지
============================================================

금지 대상:
- 노드 이름 하드코딩
- Tag / Menu / Ingredient 문자열 직접 입력
- Cypher Query 내부 문자열 직접 조합
- 파일 경로 하드코딩
- 환경 값 하드코딩

나쁜 예:
- MATCH (m:Menu {normalized_name:"중국음식"})

좋은 예:
- MATCH (m:Menu {normalized_name:$menu_name})

실무적 제언:
- 모든 값은 Parameter 또는 Constant로 관리한다.


============================================================
2. 쿼리문 상수화 (필수)
============================================================

모든 Cypher Query는 코드 내부에 직접 작성하지 않는다.

구조:

/queries/restaurant/
  - restaurant_area_menu_tag.cypher
  - restaurant_menu_only.cypher
  - restaurant_exclude_ingredient.cypher

/queries/news/
  - news_topic_search.cypher
  - news_tech_event_search.cypher

또는 Python 상수 파일:

QUERY_RESTAURANT_AREA_MENU_TAG = """
MATCH ...
"""

규칙:
- Query Template 이름과 파일명이 동일해야 한다.
- QueryBuilder는 문자열을 생성하지 않고 Template을 선택한다.

금지:
- f-string으로 Cypher 조립
- 문자열 더하기 방식 Query 생성

============================================================
3. else 문 지양
============================================================

금지:
- 복잡한 if-else 체인
- nested if-else 구조

나쁜 예:
if condition:
    ...
else:
    if condition2:
        ...
    else:
        ...

권장 방식:
- 전략 패턴
- 딕셔너리 매핑
- early return

예시:

template_map = {
    "restaurant_menu_only": TEMPLATE_01,
    "restaurant_exclusion": TEMPLATE_02
}

template = template_map.get(intent)

if template is None:
    raise UnsupportedIntentError

실무적 제언:
- Query Template 선택은 if-else가 아니라 매핑 기반으로 처리한다.


============================================================
4. import / 경로 상수화
============================================================

금지:
- 동일 경로 문자열 반복 작성
- 5줄 이상 반복되는 import 또는 경로 정의

권장:

constants/path_constants.py

QUERY_PATH = "/queries"
RESTAURANT_QUERY_PATH = f"{QUERY_PATH}/restaurant"
NEWS_QUERY_PATH = f"{QUERY_PATH}/news"

또는:

from constants.paths import RESTAURANT_QUERY_PATH

실무 기준:
- 동일 문자열 3회 이상 반복 → 상수화
- 경로 문자열 → 무조건 상수화

============================================================
5. 전역 변수 금지
============================================================

금지:
- 전역 상태 저장
- Singleton으로 상태 유지
- global keyword 사용

나쁜 예:
global query_cache

좋은 예:
- 클래스 내부 상태 관리
- 함수 파라미터 전달
- Repository 객체 사용

예시:

class QueryRepository:
    def __init__(self, query_map):
        self.query_map = query_map

실무적 제언:
- 모든 상태는 명시적으로 전달되어야 한다.
- Lambda / 멀티 환경에서 안정성 확보 목적


============================================================
6. QueryBuilder 규칙
============================================================

금지:
- QueryBuilder에서 문자열 조합
- 조건별 Cypher 분기 생성

권장:

class GraphQueryBuilder:

    def build(self, intent, slots):
        template = self._select_template(intent, slots)
        params = self._build_params(slots)

        return QueryBuildResult(
            template=template,
            params=params
        )

핵심:
- Template 선택
- Parameter 생성

둘만 수행한다.


============================================================
7. Slot → Parameter 변환 규칙
============================================================

금지:
- Slot 값을 그대로 Query에 넣기

권장:
- 반드시 normalized_value 사용

예:
slot.raw_value = "중국집"
slot.normalized_value = "중국음식"

Query:
- menu_name = "중국음식"

============================================================
8. EXCLUDES 처리 규칙
============================================================

금지:
- WHERE NOT r.name LIKE '%면%'
- 문자열 기반 필터

권장:
- 반드시 관계 기반

UserIntent -[:EXCLUDES]-> Ingredient
→ NOT EXISTS 관계 탐색

============================================================
9. Full-text Search 사용 규칙
============================================================

금지:
- Full-text 결과를 바로 최종 결과로 사용

권장:
1. 후보 노드 탐색
2. confidence 확인
3. Query Template 재실행

============================================================
10. 파일 구조 규칙
============================================================

권장 구조:

/core
  - query_builder.py
  - slot_extractor.py
  - intent_classifier.py

/constants
  - query_constants.py
  - path_constants.py

/queries
  /restaurant
  /news

/repository
  - neo4j_repository.py

/tests
  - test_scenarios.py

============================================================
11. 함수 설계 규칙
============================================================

모든 함수는 다음을 만족해야 한다.

1. 단일 책임
2. 입력/출력 명확
3. 사이드 이펙트 없음
4. 내부 상태 변경 최소화

금지:
- 하나의 함수에서
  - Slot 추출 + Query 생성 + DB 실행

권장:
- 단계별 분리

============================================================
12. 최종 보완 규칙 요약
============================================================

추가된 핵심 규칙:

1. 하드코딩 금지
2. Cypher Query는 반드시 상수화
3. else문 최소화 (매핑 기반 설계)
4. 경로 및 반복 문자열 상수화
5. 전역 변수 금지
6. QueryBuilder는 Template 선택 + Param 생성만 수행
7. Slot은 normalized_value만 사용
8. EXCLUDES는 관계 기반 처리
9. Full-text는 보조 검색으로 제한
10. 모듈화된 파일 구조 유지

============================================================
[STEP 10 보완 결론]
============================================================

이 규칙은 단순 코드 스타일이 아니라:

- 유지보수성
- 확장성
- 테스트 가능성
- 멀티 에이전트 구조 대응
- Lambda/클라우드 안정성

을 위한 필수 조건이다.
