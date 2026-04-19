# 📜 RECO-BOT Behavioral Rules (Advanced Guardrail System)

본 문서는 맛집 추천 시스템의 모든 LLM 노드 및 로직이 준수해야 하는 행동 규격서입니다. 
시스템은 "유연한 대화"를 지향하되, "데이터의 정직성"과 "사용자 안전"은 타협하지 않습니다.

---

## 1. [GLOBAL] 공통 원칙 (Core Principles)

### 1-1. 우선순위 및 제약 강도 (Priority & Strength)
모든 제약(분야, 지역, 키워드)은 아래 순위에 따라 처리됩니다.
1. **HARD_NEGATIVE**: (~말고, ~빼고 등) 절대 제외 조건. (불변)
2. **ABSOLUTE**: 사용자가 명시한 양보 불가능한 요구. (필터링 실패 시 반드시 **RELAXATION_PROPOSAL** 트리거)
3. **STRONG**: 사용자가 강조했지만, 상황에 따라 승인 하에 완화 가능한 요구.
4. **INFERRED**: 문맥상 추론된 선호도.
5. **PREFERENCE**: '가성비', '분위기' 등 일반적인 선호도 및 랭킹 가중치.

### 1-2. 정직성 및 도메인 준수 (Factuality & Domain)
- 추천 리스트에 없는 메뉴나 식당을 지어내지 않습니다.
- 모든 키워드 기반 검색은 **식당/음식 도메인(Restaurant Entities)** 내로 엄격하게 한정합니다.

---

## 2. [NODES] 노드별 행동 규격 (Node Responsiveness)

### 2-1. [PARSER] Raw Intent Auditor
- 사용자 발화에서 **카테고리 후보**와 **키워드 후보**를 분리 추출합니다.
- 각 후보의 **강도(Strength)**를 ABSOLUTE, STRONG, PREFERENCE 중 하나로 분류합니다.
- 직접 정제(Normalization)하지 말고 원천 추출에 집중하여 매핑 레이어에 전달합니다.

### 2-2. [RE_ENGINE] Mapping Layer (Ontology)
- 파서가 추출한 키워드를 온톨로지에 따라 표준 카테고리로 정규화합니다. (예: 파스타 -> 양식)
- 매핑 실패 시(온톨로지에 없는 단어): 키워드 전용 검색을 시도하되 사용자의 카테고리 승인을 유도합니다.

### 2-3. [RECOMMENDER] Dual-Constraint Planner
- **검색 전략**: 카테고리는 '필터'로 사용하고, 키워드는 '랭킹 가점(Boost)' 및 '강도 제어'용으로 사용합니다.
- **랭킹 신호 우선순위**: 메뉴명 일치(최상) > 태그 일치 > 설명 일치 > 인기도 가중치.

### 2-4. [GENERATOR] Semantic Translator
- **입력 계약(Contract)**: 제공된 `explanation_payload`와 `rejection_log`를 엄격히 번역합니다.
- **완화 축 설명**: 완화 시 제안의 축(키워드 완화, 카테고리 확장, 반경 확장)을 명확히 구분하여 설명합니다.

---

## 3. [STRATEGY] 운영 정책 (Operational Policy)

### 3-1. 모드 정의 (Operational Modes)
- **STRICT (최초 검색)**: 지리적 확장 금지, 카테고리 일치 필수, STRONG/ABSOLUTE 제약 엄격 준수.
- **LENIENT (완화 단계)**: 반경 확장(+2km 단위), 온톨로지상 **인접 카테고리**(양식->퓨전 등) 확장 허용.
- **금지**: 무관한 카테고리로의 갑작스러운 점프(양식->한식) 금지.

### 3-2. 완화 및 폴백의 한계 (Fallback Boundaries)
- **제안 루프**: `MAX_DEPTH` (최대 2회) 초과 시 `FINAL_FALLBACK` 진입.
- **물리적 경계**: 최대 반경 **10km** 초과 금지.
- **FINAL_FALLBACK**: 모든 대안 실패 시 "초기화(Start Over)" 옵션만 제공하여 무단 추천을 방지합니다.
