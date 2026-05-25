# KAG 메뉴 정규화 + Recipe Ingredient 패치 최종 반영본

작성일: 2026-05-12

---

# 1. 문서 목적

본 문서는 기존 KAG/ETL 구조를 유지하면서 다음 기능을 추가하기 위한 1차 패치 설계안이다.

```text
가게 메뉴명 수집
-> Rule + Similarity 기반 메뉴 정규화
-> canonical menu 생성
-> 만개의레시피 검색
-> ingredient 추출
-> KAG Menu-Ingredient 관계 보강
```

핵심 원칙:

```text
Menu 노드는 전역 공유 개념 노드로 유지한다.
식당별 원본 메뉴명/가격/표시명은 Menu 노드가 아니라
Restaurant-[:SELLS]->Menu 관계 속성으로 보존한다.
```

---

# 2. 최종 결론

1차 패치에서는 기존 KAG 구조를 유지한다.

```text
(:Restaurant)-[:SELLS]->(:Menu)
(:Menu)-[:CONTAINS]->(:Ingredient)
```

다음 노드는 1차 패치에서 도입하지 않는다.

```text
StoreMenu
CanonicalMenu
Recipe
```

이유:

```text
현재 KAG의 Menu는 normalized_name unique 제약을 가진 전역 공유 노드이다.
따라서 여러 식당이 동일 Menu 노드를 공유한다.
Menu 노드에 raw/display/price를 넣으면 마지막 적재값으로 덮어쓰기 오염이 발생할 수 있다.
```

---

# 3. 최종 KAG 스키마

## 3.1 Menu 노드

`Menu`는 전역 공유 개념 노드로 사용한다.

```cypher
(:Menu {
  normalized_name: "제육볶음",
  canonical_name: "제육볶음",
  name: "제육볶음"
})
```

Menu 노드에 저장 가능한 값:

```text
normalized_name
canonical_name
name
category_hint
ingredient_source_priority
updated_at
```

Menu 노드에 저장하면 안 되는 값:

```text
raw_menu_name
display_menu_name
price
store-specific menu text
menu_confidence
menu_normalization_status
```

---

## 3.2 Restaurant-SELLS-Menu 관계

식당별 메뉴 정보는 `SELLS` 관계 속성으로 저장한다.

```cypher
(:Restaurant)-[:SELLS {
  raw_menu_name: "직화 제육 정식 2인",
  display_menu_name: "직화 제육 정식 2인",
  price: 12000,
  recipe_search_keyword: "제육볶음",
  menu_confidence: 0.94,
  menu_normalization_status: "NORMALIZED",
  normalization_method: "RULE_SIMILARITY"
}]->(:Menu {normalized_name: "제육볶음"})
```

장점:

```text
1. Menu는 전역 개념 노드로 유지된다.
2. 식당별 원본 메뉴명은 관계 속성으로 안전하게 보존된다.
3. 동일 canonical menu를 여러 식당이 공유해도 원본 메뉴명이 덮어써지지 않는다.
4. StoreMenu 노드를 추가하지 않고도 1차 패치 범위를 유지할 수 있다.
```

---

## 3.3 Ingredient 노드

`Ingredient`도 기존 제약조건에 맞춰 `normalized_name` 중심으로 유지한다.

```cypher
(:Ingredient {
  normalized_name: "돼지고기",
  name: "돼지고기"
})
```

주의:

```text
Ingredient는 name이 아니라 normalized_name으로 MERGE한다.
현재 KAG schema의 ingredient_normalized_name unique 제약과 맞추기 위함이다.
```

---

## 3.4 Menu-Ingredient 관계

재료 관계는 기존 구조를 유지하되 edge 속성을 확장한다.

```cypher
(:Menu)-[:CONTAINS {
  source: "RECIPE10000",
  source_url: "https://...",
  confidence: 0.91,
  fallback_used: false
}]->(:Ingredient {normalized_name: "돼지고기"})
```

---

# 4. 원본 메뉴명 보존 원칙

원본 메뉴명은 프론트 서비스에서 그대로 노출되어야 한다.

단, KAG에서는 `Menu` 노드 속성이 아니라 `SELLS` 관계 속성에 저장한다.

```text
raw_menu_name
display_menu_name
price
```

저장 위치:

```text
Restaurant-[:SELLS]->Menu 관계 속성
```

금지:

```text
Menu.name = raw_menu_name
Menu.display_name = raw_menu_name
Menu.price = price
```

---

# 5. 메뉴 정규화 전략

## 5.1 최종 선택

```text
Rule + Similarity 기반 정규화
```

## 5.2 처리 흐름

```text
raw_menu_name
-> text cleaning
-> keyword extraction
-> candidate generation
-> similarity score 계산
-> confidence 계산
-> normalized_name/canonical_name 결정
```

---

# 6. Cleaning Rule

## 6.1 제거 대상

```text
매콤
직화
수제
프리미엄
시그니처
대표
인기
BEST
정식
세트
한상
1인
2인
런치
디너
곱빼기
대
중
소
숫자
특수문자
```

## 6.2 예시

```text
"매콤 직화 제육 정식 2인"
-> "제육"
-> "제육볶음"
```

```text
"BEST 수제 바질크림파스타"
-> "바질크림파스타"
```

---

# 7. Candidate Rule

핵심 키워드 기반으로 표준 메뉴 후보를 생성한다.

```text
제육 -> 제육볶음
김치 + 찌개 -> 김치찌개
된장 + 찌개 -> 된장찌개
크림 + 파스타 -> 크림파스타
불고기 + 덮밥 -> 불고기덮밥
```

---

# 8. Similarity Score

## 8.1 점수 계산

```text
final_score =
  keyword_score * 0.5
+ text_similarity_score * 0.3
+ category_score * 0.2
```

## 8.2 Threshold

```text
final_score >= 0.88
-> NORMALIZED

0.70 <= final_score < 0.88
-> REVIEW_CANDIDATE

final_score < 0.70
-> LOW_CONFIDENCE
```

---

# 9. Recipe 수집 대상 생성 정책

## 9.1 핵심 원칙

Recipe 수집 대상은 Stage 3 Validation & Normalization 결과에서 생성한다.

수집 대상 조건:

```text
menu_normalization_status = NORMALIZED
```

1차 패치에서는 다음 상태를 recipe crawler로 전달하지 않는다.

```text
REVIEW_CANDIDATE
LOW_CONFIDENCE
```

즉, 자동 수집 대상은 `NORMALIZED`만 허용한다.

---

## 9.2 Recipe 수집 대상 예시

```json
{
  "restaurant_id": "rest_001",
  "raw_menu_name": "직화 제육 정식 2인",
  "display_menu_name": "직화 제육 정식 2인",
  "normalized_name": "제육볶음",
  "canonical_name": "제육볶음",
  "recipe_search_keyword": "제육볶음",
  "menu_confidence": 0.94,
  "menu_normalization_status": "NORMALIZED"
}
```

---

# 10. Recipe Collector/Parser 위치

## 10.1 추가 위치

```text
etl/meal/src/collectors/platforms/recipe10000_collector.py
etl/meal/src/services/parsers/recipe10000_parser.py
```

## 10.2 Registry 등록

```text
etl/meal/src/core/registry.py
```

## 10.3 Collector 책임

```text
recipe_search_keyword 기반 검색 URL 생성
검색 결과 HTML 저장
recipe detail HTML 저장
raw evidence 보존
```

금지:

```text
메뉴 정규화 판단
recipe 수집 여부 정책 판단
retry/reprocess 판단
```

## 10.4 Parser 책임

```text
recipe_title 추출
recipe_url 추출
ingredient_raw_text 추출
serving 정보 추출
```

---

# 11. ETL 내부에 추가하는 이유

Recipe 수집은 KAG 쪽 별도 모듈이 아니라 ETL meal 내부 collector/parser로 추가한다.

이유:

```text
1. 기존 failcheck 구조 재사용 가능
2. 기존 JSONL 산출물 구조 재사용 가능
3. 기존 HivePathBuilder 재사용 가능
4. 기존 run_attempt 구조 유지 가능
5. 기존 retry/reprocess 정책 재사용 가능
```

---

# 12. 저장 경로 정책

## 12.1 RECIPE category_cd 사용 여부

1차 패치에서는 `RECIPE`를 `category_cd`로 직접 사용하지 않는다.

이유:

```text
현재 category_cd는 코드 테이블 기반 운영 코드이다.
RECIPE를 임의 category_cd로 쓰면 코드 테이블 원칙과 충돌할 수 있다.
```

## 12.2 최종 방식

기존 `category_cd`는 유지한다.

Recipe/Ingredient 메타데이터 여부는 record 내부 필드로 구분한다.

```json
{
  "category_cd": "SC01",
  "metadata_type": "RECIPE_INGREDIENT",
  "source_platform": "10000recipe"
}
```

저장 경로 예시:

```text
process=cleansing/category_cd=SC01/year=2026/month=05/day=12/status=success/
```

---

# 13. Ingredient 수집 우선순위

1차 패치에서는 기존 CSV fallback을 유지한다.

우선순위:

```text
1. recipe 기반 ingredient
2. menu_ingredient.csv fallback
3. ingredient 없음 처리
```

Recipe 기반 결과가 정상 수집되면 이를 우선 사용한다.

Recipe 수집 실패 또는 confidence 부족 시 기존 CSV fallback을 사용한다.

---

# 14. CSV Fallback 유지 이유

Recipe 기반 수집은 다음 실패 가능성이 있다.

```text
검색 결과 없음
selector 변경
recipe detail 접근 실패
ingredient parsing 실패
ingredient normalization 실패
```

따라서 기존 `menu_ingredient.csv` fallback은 제거하지 않는다.

---

# 15. Stage별 패치 상세

## 15.1 Stage 2 Candidate Parsing

Stage 2는 원본 메뉴명 추출만 수행한다.

```json
{
  "restaurant_id": "rest_001",
  "raw_menu_name": "직화 제육 정식 2인",
  "menu_price": 12000
}
```

금지:

```text
canonical_name 결정
recipe_search_keyword 생성
recipe 수집 여부 판단
```

---

## 15.2 Stage 3 Validation & Normalization

Stage 3은 메뉴별로 다음 필드를 생성한다.

```json
{
  "raw_menu_name": "직화 제육 정식 2인",
  "display_menu_name": "직화 제육 정식 2인",
  "normalized_name": "제육볶음",
  "canonical_name": "제육볶음",
  "recipe_search_keyword": "제육볶음",
  "menu_confidence": 0.94,
  "menu_normalization_status": "NORMALIZED",
  "normalization_method": "RULE_SIMILARITY"
}
```

`REVIEW_CANDIDATE` 예시:

```json
{
  "raw_menu_name": "돼지불고기 제육덮밥",
  "display_menu_name": "돼지불고기 제육덮밥",
  "normalized_name": null,
  "canonical_name": null,
  "recipe_search_keyword": null,
  "menu_confidence": 0.76,
  "menu_normalization_status": "REVIEW_CANDIDATE",
  "normalization_method": "RULE_SIMILARITY"
}
```

`LOW_CONFIDENCE` 예시:

```json
{
  "raw_menu_name": "시그니처 한상",
  "display_menu_name": "시그니처 한상",
  "normalized_name": null,
  "canonical_name": null,
  "recipe_search_keyword": null,
  "menu_confidence": 0.31,
  "menu_normalization_status": "LOW_CONFIDENCE",
  "normalization_method": "RULE_SIMILARITY"
}
```

---

## 15.3 Stage 4 Save / KAG Importer

KAG importer는 다음 방식으로 저장한다.

```cypher
MERGE (menu:Menu {normalized_name: $normalized_name})
SET menu.canonical_name = $canonical_name,
    menu.name = $canonical_name

MERGE (restaurant)-[s:SELLS]->(menu)
SET s.raw_menu_name = $raw_menu_name,
    s.display_menu_name = $display_menu_name,
    s.price = $price,
    s.recipe_search_keyword = $recipe_search_keyword,
    s.menu_confidence = $menu_confidence,
    s.menu_normalization_status = $menu_normalization_status,
    s.normalization_method = $normalization_method
```

Ingredient 관계:

```cypher
MERGE (ingredient:Ingredient {normalized_name: $ingredient_name})
SET ingredient.name = $ingredient_name

MERGE (menu)-[c:CONTAINS]->(ingredient)
SET c.source = $ingredient_source,
    c.source_url = $source_url,
    c.confidence = $ingredient_confidence,
    c.fallback_used = $fallback_used
```

주의:

```text
Ingredient는 name이 아니라 normalized_name으로 MERGE한다.
Menu에는 price를 저장하지 않는다.
식당별 price는 SELLS 관계 속성에만 저장한다.
```

---

# 16. ReasonCode 추가

추가 ReasonCode:

```text
AMBIGUOUS_MENU_NAME
LOW_CONFIDENCE_MENU_NORMALIZATION
REVIEW_CANDIDATE_MENU_NORMALIZATION
RECIPE_SEARCH_EMPTY
RECIPE_SELECTOR_MISMATCH
INGREDIENT_PARSE_FAILED
INGREDIENT_NORMALIZATION_FAILED
KAG_GRAPH_BUILD_FAILED
```

---

# 17. Resolver 매핑 필수

ReasonCode를 추가할 때는 반드시 다음도 함께 수정한다.

```text
etl/meal/src/core/policy/reason_code.py
etl/meal/src/core/policy/exceptions.py
etl/meal/src/core/policy/resolver.py
reason_code -> action 매핑 테스트
```

예시 방향:

```text
LOW_CONFIDENCE_MENU_NORMALIZATION -> warning
REVIEW_CANDIDATE_MENU_NORMALIZATION -> manual_check 또는 warning
RECIPE_SEARCH_EMPTY -> warning 또는 reprocess 후보
RECIPE_SELECTOR_MISMATCH -> reprocess
INGREDIENT_PARSE_FAILED -> reprocess
INGREDIENT_NORMALIZATION_FAILED -> reprocess 또는 warning
KAG_GRAPH_BUILD_FAILED -> reprocess
```

단, Stage 내부에서 action을 결정하지 않는다.

---

# 18. Fail 처리 원칙

```text
Stage
-> fail JSONL 저장
-> failcheck 전달
-> Resolver action 결정
```

금지:

```text
Stage 내부 retry 판단
Stage 내부 reprocess 판단
Stage 내부 alert 판단
Stage 내부 drop 판단
```

---

# 19. 테스트 기준

```text
1. Menu 노드에 raw/display/price가 저장되지 않는지 테스트
2. raw_menu_name이 SELLS 관계 속성에 저장되는지 테스트
3. 동일 normalized_name을 여러 식당이 공유해도 원본 메뉴명이 섞이지 않는지 테스트
4. Ingredient가 normalized_name 기준으로 MERGE되는지 테스트
5. Rule + Similarity threshold 테스트
6. NORMALIZED만 recipe crawler로 전달되는지 테스트
7. REVIEW_CANDIDATE가 recipe crawler로 전달되지 않는지 테스트
8. LOW_CONFIDENCE가 recipe crawler로 전달되지 않는지 테스트
9. recipe parser selector 테스트
10. ingredient normalization 테스트
11. recipe 기반 ingredient 우선순위 테스트
12. menu_ingredient.csv fallback 테스트
13. ReasonCode -> Resolver action 매핑 테스트
14. Hive path 생성 테스트
15. duplicate canonical menu 방지 테스트
16. KAG CONTAINS edge source/fallback_used 속성 테스트
```

---

# 20. 1차 패치 범위

## 포함

```text
기존 Menu 구조 유지
Menu 노드는 normalized_name/canonical_name 중심으로 유지
SELLS 관계 속성에 raw/display/price 저장
Ingredient는 normalized_name 중심으로 유지
Rule + Similarity 메뉴 정규화 추가
recipe_search_keyword 생성
recipe10000_collector.py 추가
recipe10000_parser.py 추가
registry.py 등록
recipe 기반 ingredient 수집
menu_ingredient.csv fallback 유지
ReasonCode + Resolver 매핑 추가
KAG importer 확장
```

## 제외

```text
StoreMenu 노드 신규 도입
CanonicalMenu 노드 신규 도입
Recipe 노드 신규 도입
RECIPE category_cd 신규 도입
KAG 전체 스키마 대개편
REVIEW_CANDIDATE 자동 recipe 수집
LOW_CONFIDENCE 자동 recipe 수집
Menu 노드에 식당별 raw/display/price 저장
Ingredient name 기준 MERGE
```

---

# 21. 최종 흐름

```text
가게 메뉴 raw 수집
-> Stage 2 raw_menu_name 추출
-> Stage 3 Rule + Similarity 정규화
-> NORMALIZED 메뉴만 recipe_search_keyword 생성
-> recipe10000 collector/parser 실행
-> ingredient 정규화
-> KAG importer 반영
```

KAG 반영 구조:

```text
Restaurant
  -[:SELLS {raw_menu_name, display_menu_name, price, confidence}]
    -> Menu {normalized_name, canonical_name}

Menu
  -[:CONTAINS {source, source_url, confidence, fallback_used}]
    -> Ingredient {normalized_name, name}
```

---

# 22. 구현 시 현재 코드 수정 포인트

현재 `kag/src/kag_graph/hive_importer.py`는 다음 형태이므로 수정이 필요하다.

현재:

```cypher
MERGE (menu:Menu {normalized_name: $menu_name})
SET menu.name = $menu_name,
    menu.price = $price,
    menu.menu_type = "dish"
MERGE (restaurant)-[:SELLS]->(menu)
```

변경 방향:

```cypher
MERGE (menu:Menu {normalized_name: $normalized_name})
SET menu.name = $canonical_name,
    menu.canonical_name = $canonical_name,
    menu.menu_type = "dish"

MERGE (restaurant)-[s:SELLS]->(menu)
SET s.raw_menu_name = $raw_menu_name,
    s.display_menu_name = $display_menu_name,
    s.price = $price,
    s.recipe_search_keyword = $recipe_search_keyword,
    s.menu_confidence = $menu_confidence,
    s.menu_normalization_status = $menu_normalization_status,
    s.normalization_method = $normalization_method
```

현재 Ingredient 관계도 다음 형태이므로 수정이 필요하다.

현재:

```cypher
MERGE (ingredient:Ingredient {normalized_name: $ingredient_name})
SET ingredient.name = $ingredient_name
MERGE (menu)-[:CONTAINS]->(ingredient)
```

변경 방향:

```cypher
MERGE (ingredient:Ingredient {normalized_name: $ingredient_name})
SET ingredient.name = $ingredient_name

MERGE (menu)-[c:CONTAINS]->(ingredient)
SET c.source = $ingredient_source,
    c.source_url = $source_url,
    c.confidence = $ingredient_confidence,
    c.fallback_used = $fallback_used
```

---

# 23. 최종 정리

이번 1차 패치의 최종 방향은 다음이다.

```text
프론트 원본 메뉴명 보존
+
Menu 전역 개념 노드 유지
+
식당별 메뉴 정보는 SELLS 관계 속성으로 분리
+
Ingredient는 normalized_name 기준으로 유지
+
NORMALIZED 메뉴만 recipe 수집
+
recipe ingredient 우선, CSV fallback 유지
+
ReasonCode 추가 시 Resolver 매핑 필수
```

이 구조는 다음을 보장한다.

```text
1. 기존 KAG 스키마를 크게 깨지 않는다.
2. Menu unique 제약과 충돌하지 않는다.
3. Ingredient unique 제약과 충돌하지 않는다.
4. 식당별 원본 메뉴명이 덮어써지지 않는다.
5. KAG ingredient 품질을 recipe 기반으로 개선할 수 있다.
6. recipe 실패 시 기존 CSV fallback으로 운영 안정성을 유지한다.
```
