"""
core/nodes/parser.py — 사용자 의도 파싱 노드 (Intent Auditor)

사용자의 자연어 발화를 분석하여 구조화된 검색 조건으로 변환합니다.

[파이프라인 단계]
    Stage 1: LLM을 통한 슬롯 추출 (area, category, keywords)
    Stage 2: 키워드 분류 및 강도 할당 (HARD_FILTER, SOFT_PREFERENCE, RANKING_SIGNAL)
    Stage 3: MSC 계층 분류 (Strong/Structural/Weak)
    Stage 4: 검색 vs 재질의 결정 (SEARCH or CLARIFICATION)

[입력]
    state["user_input"]   : 사용자 발화 원문
    state["chat_history"] : 이전 대화 이력

[출력]
    area, category, hard_filters, soft_preferences,
    ranking_signals, keyword_strengths, excluded_*, 
    meta_intent, ui_mode, clarification_needed 등
"""

import json
import re
from typing import Optional

from langchain_core.prompts import ChatPromptTemplate

from core.state import AgentState
from core.llm import llm_extra
from utils.logger import get_logger
from knowledge import rule_engine

logger = get_logger("ParserNode")


# ═════════════════════════════════════════════
# 헬퍼 함수 (Stage 0: 전처리)
# ═════════════════════════════════════════════

def normalize_area_text(text: str) -> Optional[str]:
    """
    지명 텍스트를 정규화합니다.

    처리 과정:
        1. 수식어 제거: "강남역 근처" → "강남역" → "강남"
        2. 부분 일치 보정: "금천" → "금천구"

    Args:
        text: 원본 지명 텍스트

    Returns:
        정규화된 지명 문자열 또는 None (빈 입력)
    """
    if not text:
        return None

    # 1. 수식어 제거 ("~근처", "~주변", "~인근", "~역")
    clean_text = text
    for stop in rule_engine.ontology.STOP_WORDS_AREA:
        if clean_text.endswith(stop):
            clean_text = clean_text.replace(stop, "").strip()

    # 2. 부분 일치 보정 (약어 → 정식 행정구역명)
    suffix_map = {
        "금천": "금천구", "구로": "구로구",
        "강남": "강남구", "성수": "성수동",
    }
    if clean_text in suffix_map:
        clean_text = suffix_map[clean_text]

    return clean_text if clean_text else None


def validate_area_slot(raw_area: str, raw_keywords: list) -> tuple:
    """
    지명(area) 슬롯의 유효성을 검증하고,
    비지역 토큰을 올바른 슬롯으로 재분류합니다.

    LLM이 음식 이름이나 상황 키워드를 area로 잘못 추출하는 경우를
    감지하여 keyword 슬롯으로 이동시킵니다.

    Args:
        raw_area    : LLM이 추출한 원본 지명
        raw_keywords: LLM이 추출한 키워드 리스트 (재분류 시 여기에 추가)

    Returns:
        (검증된_area, 업데이트된_keywords) 튜플
        - area가 유효하지 않으면 None 반환
        - 비지역 토큰은 keywords에 추가됨
    """
    if not raw_area:
        return None, raw_keywords

    normalized = normalize_area_text(raw_area)

    # 1. 금지 토큰 체크 (LLM이 "알 수 없음" 등을 출력한 경우)
    if normalized in ["알 수 없음", "none", "null"]:
        return None, raw_keywords

    # 2. 상황/속성 토큰 재분류 (Slot Reclassification)
    # 예: LLM이 "비건"을 area로 추출한 경우 → keyword로 이동
    is_food_or_lifestyle = (
        rule_engine.ontology.map_keyword(normalized)
        or rule_engine.ontology.get_broad_categories(normalized)
        or normalized in ["혼밥", "데이트", "가족", "주차", "발렛", "비건"]
    )

    if is_food_or_lifestyle:
        logger.warning(
            f"      -> Slot Reclassification: '{normalized}' is not an area. "
            f"Moving to keywords."
        )
        # 재분류 시 적절한 타입 할당
        k_type = "SOFT_PREFERENCE"
        if normalized in ["주차", "발렛"]:
            k_type = "FACILITY_FILTER"
        elif normalized in ["비건"]:
            k_type = "DIETARY_CONSTRAINT"

        raw_keywords.append({
            "value": normalized, "type": k_type, "strength": "STRONG"
        })
        return None, raw_keywords

    # 3. 행정구역 패턴 매칭 (구, 동, 역 등)
    if rule_engine.ontology.is_geographic_unit(normalized):
        return normalized, raw_keywords

    # 4. 불확실한 경우 → 안전하게 null 처리
    logger.warning(
        f"      -> Unclear Area: '{normalized}' does not match patterns. Nullifying."
    )
    return None, raw_keywords


def sanitize_val(v):
    """
    LLM 출력에서 플레이스홀더 값을 정제합니다.

    "...", "none", "null", 빈 문자열 등을 None으로 변환하고
    문자열 양쪽 공백을 제거합니다.

    Args:
        v: 정제할 값 (문자열 또는 기타 타입)

    Returns:
        정제된 값 또는 None
    """
    if isinstance(v, str):
        v = v.strip()
        if v.lower() in ["...", "none", "null", ""]:
            return None
    return v


# ═════════════════════════════════════════════
# Stage 1: LLM 프롬프트 구성 및 호출
# ═════════════════════════════════════════════

def _build_parser_prompt(state: AgentState, behavioral_rules: str) -> dict:
    """
    의도 파싱을 위한 LLM 프롬프트를 구성합니다.

    프롬프트에는 다음이 포함됩니다:
        - 시스템 역할 정의 (Intent Auditor)
        - 슬롯 규격 (area, category, keywords, meta)
        - 분류 가이드라인 (HARD_FILTER vs SOFT_PREFERENCE vs RANKING_SIGNAL)
        - 가드레일 (부정/긍정 표현 구분)
        - 예시 (Few-shot)
        - 이전 대화 컨텍스트

    Args:
        state           : 현재 AgentState
        behavioral_rules: RULE.MD에서 로드된 행동 규칙 텍스트

    Returns:
        LLM invoke에 전달할 파라미터 딕셔너리
    """
    # 대화 이력을 텍스트로 직렬화
    chat_history_str = ""
    for msg in state.get("chat_history", []):
        role = "사용자" if msg.get("role") == "user" else "봇"
        chat_history_str += f"{role}: {msg.get('content')}\n"

    prompt = ChatPromptTemplate.from_template(
        "당신은 고도로 정밀한 맛집 검색 의도 감사관(Intent Auditor)입니다.\n"
        "사용자의 발화를 분석하여 아래 슬롯 규격에 따라 정보를 엄격히 분산 배치하세요.\n\n"
        "{behavioral_rules}\n\n"
        "[슬롯 규격]\n"
        "1. area: 지리적 행정 구역만 허용 (예: 강남, 홍대). 음식/메뉴 이름은 절대 금지.\n"
        "2. category: '한식', '양식', '일식', '중식', '아시아음식' 등 대분류.\n"
        "   - **주의**: 사용자가 명시하지 않은 카테고리를 절대 임의로 추론하거나 기본값(한식 등)으로 채우지 마십시오 (MUST NOT).\n"
        "   - 카테고리가 불분명하면 null로 비워두십시오.\n"
        "3. keywords: 발화에서 추출된 모든 특징적 토큰들.\n"
        "   - type: HARD_FILTER (음식종류, 제외/포함), SOFT_PREFERENCE (분위기, 상황), RANKING_SIGNAL (맛집, 추천)\n"
        "   - strength: ABSOLUTE (필수), STRONG (강한 선호), PREFERENCE (일반)\n"
        "   - is_negative: 제외/부정 표현 여부 (bool)\n"
        "4. meta: \n"
        "   - intent_type: recommend, search, compare, history_recall\n"
        "   - confidence: 분석 신뢰도 (0.0~1.0)\n\n"
        "[가드레일]\n"
        "- '파스타', '국수' 처럼 결과 집합을 직접 제한하거나 메인 메뉴인 경우 HARD_FILTER입니다.\n"
        "- '조용한', '분위기 있는', '데이트' 처럼 점수에 반영되어야 하는 정성적 조건은 SOFT_PREFERENCE입니다.\n"
        "- '맛집', '추천', '유명한', '평이 좋은', '인기 있는', '무난한', '괜찮은' 등은 RANKING_SIGNAL입니다. 이들은 매우 중요하므로 누락하지 마세요.\n"
        "- **긍정적 강조**: '~ 위주로', '~ 중심으로', '~ 위주의'는 해당 항목의 선호(POSITIVE)를 나타냅니다. 절대 제외 조건으로 파싱하지 마세요.\n"
        "- **부정적 제외**: '~ 제외', '~ 말고', '~ 빼고', '~ 없이'와 같은 표현만 `is_negative: true`로 설정하세요.\n\n"
        "[이전 대화 내역]\n{chat_history_str}\n\n"
        "결과 형태 (JSON): {{\n"
        "  'area': '...', \n"
        "  'category': null, \n"
        "  'keywords': [\n"
        "     {{'value': '파스타', 'type': 'HARD_FILTER', 'strength': 'ABSOLUTE', 'is_negative': false}}\n"
        "  ],\n"
        "  'meta': {{'intent_type': 'recommend', 'confidence': 0.9}}\n"
        "}}\n\n"
        "예시 1: '강남역 맛집 추천해줘'\n"
        "결과: {{'area': '강남역', 'keywords': [{{'value': '맛집', 'type': 'RANKING_SIGNAL'}}]}}\n\n"
        "예시 2: '조용한 파스타집, 일식은 빼고'\n"
        "결과: {{'keywords': [{{'value': '조용한', 'type': 'SOFT_PREFERENCE'}}, {{'value': '파스타', 'type': 'HARD_FILTER'}}, {{'value': '일식', 'is_negative': true}}]}}\n\n"
        "예시 3: '면 요리 잘하는 곳, 중국집 제외'\n"
        "결과: {{'keywords': [{{'value': '면 요리', 'type': 'HARD_FILTER'}}, {{'value': '잘하는', 'type': 'RANKING_SIGNAL'}}, {{'value': '중국집', 'is_negative': true}}]}}\n\n"
        "사용자 최신 질문: {user_input}"
    )

    return {
        "prompt": prompt,
        "params": {
            "behavioral_rules": behavioral_rules,
            "chat_history_str": chat_history_str if chat_history_str else "(없음)",
            "user_input": state["user_input"],
        },
    }


# ═════════════════════════════════════════════
# Stage 2: 키워드 분류 및 강도 할당
# ═════════════════════════════════════════════

def _classify_keywords(raw_keywords: list) -> dict:
    """
    LLM이 추출한 키워드를 카테고리별로 분류하고 강도를 할당합니다.

    분류 체계:
        - HARD_FILTER      : 결과 집합을 직접 제한 (파스타, 스시 등)
        - SOFT_PREFERENCE   : 점수에 반영되는 정성적 선호 (조용한, 데이트 등)
        - RANKING_SIGNAL    : 점수 가중치만 조정 (맛집, 유명한 등)
        - DIETARY_CONSTRAINT: 식이 제한 (비건 등)
        - Negative 계열     : 제외 조건 (excluded_categories, excluded_names, negative_keywords)

    Args:
        raw_keywords: LLM이 추출한 키워드 딕셔너리 리스트

    Returns:
        분류 결과 딕셔너리:
            hard_filters, soft_preferences, ranking_signals,
            excluded_categories, excluded_names, negative_keywords,
            dietary_constraints, positive_keywords, keyword_strengths
    """
    # 결과 컨테이너 초기화
    hard_filters = []
    soft_preferences = []
    ranking_signals = []
    excluded_categories = []
    excluded_names = []
    negative_keywords = []
    dietary_constraints = []
    positive_keywords = []
    keyword_strengths = {}

    # 온톨로지 참조 데이터
    generic_signals_map = rule_engine.ontology.RANKING_SIGNALS
    domain_generic_terms = rule_engine.ontology.DOMAIN_GENERIC_TERMS

    for kw in raw_keywords:
        val = sanitize_val(kw.get("value"))
        if val is None:
            continue

        # ── 1. 도메인 일반 용어 필터링 ──────
        # "맛집", "식당" 등은 검색 필터가 아닌 진입 마커로만 사용
        if val in domain_generic_terms:
            logger.info(f"      -> [Generic Marker] '{val}'")
            continue

        k_type = kw.get("type", "HARD_FILTER")
        k_strength = kw.get("strength", "PREFERENCE")
        is_neg = kw.get("is_negative", False)

        # ── 2. 부정 제약 처리 (제외 조건) ──────
        # "~말고", "~빼고" 표현은 최우선으로 처리
        if is_neg:
            mapped_cat = rule_engine.ontology.map_keyword(val)
            log_tag = (
                "Category"
                if mapped_cat or val in ["중식", "한식", "일식", "양식", "아시아음식"]
                else ("Name" if "점" in val or "식당" in val else "Keyword")
            )
            logger.info(f"      -> [Exclusion] '{val}' classified as Negative {log_tag}")

            if mapped_cat or val in ["중식", "한식", "일식", "양식", "아시아음식"]:
                excluded_categories.append(mapped_cat or val)
            elif "점" in val or "식당" in val:
                excluded_names.append(val)
            else:
                negative_keywords.append(val)
            continue

        # ── 3. 랭킹 시그널 분리 ──────
        # "맛집", "유명한" 등은 필터가 아닌 점수 가중치
        if val in generic_signals_map or k_type == "RANKING_SIGNAL":
            logger.info(f"      -> [Signal] '{val}' classified as Ranking Boost")
            ranking_signals.append(val)
            continue

        # ── 4. 재분류 가드레일 ──────
        # LLM이 사회적 맥락을 HARD_FILTER로 분류해도 SOFT_PREFERENCE로 하향
        is_social_context = val in [
            "혼밥", "데이트", "가족", "조용", "분위기", "아이", "아이와", "키즈"
        ]
        is_operational = val in [
            "주차", "발렛", "배달", "예약", "24시", "영업중"
        ]

        if is_social_context:
            logger.info(
                f"      -> [Audit] '{val}' reclassified as SOFT_PREFERENCE "
                f"(Reason: SOCIAL_CONTEXT_NOT_SEARCHABLE)"
            )
            k_type = "SOFT_PREFERENCE"
        elif is_operational:
            logger.info(
                f"      -> [Audit] '{val}' reclassified as DIETARY_CONSTRAINT "
                f"(Reason: OPERATIONAL_CONSTRAINT)"
            )
            k_type = "DIETARY_CONSTRAINT"

        # ── 5. 최종 분류 ──────
        logger.info(f"      -> [Keyword] '{val}' (Type: {k_type}, Strength: {k_strength})")
        if k_type == "HARD_FILTER":
            hard_filters.append(val)
            positive_keywords.append(val)
            keyword_strengths[val] = k_strength
        elif k_type == "DIETARY_CONSTRAINT":
            dietary_constraints.append(val)
            positive_keywords.append(val)
            keyword_strengths[val] = k_strength
        else:  # SOFT_PREFERENCE
            soft_preferences.append(val)
            positive_keywords.append(val)
            keyword_strengths[val] = k_strength

    return {
        "hard_filters": hard_filters,
        "soft_preferences": soft_preferences,
        "ranking_signals": ranking_signals,
        "excluded_categories": excluded_categories,
        "excluded_names": excluded_names,
        "negative_keywords": negative_keywords,
        "dietary_constraints": dietary_constraints,
        "positive_keywords": positive_keywords,
        "keyword_strengths": keyword_strengths,
    }


# ═════════════════════════════════════════════
# Stage 3: MSC 계층 분류 (Multi-Signal Classification)
# ═════════════════════════════════════════════

def _classify_msc(
    raw_area: str,
    mapped_category: str,
    hard_filters: list,
    dietary_constraints: list,
    soft_preferences: list,
    ranking_signals: list,
) -> dict:
    """
    추출된 슬롯을 Strong/Structural/Weak 3계층으로 분류합니다.

    [계층 정의]
        Strong     : 검색의 핵심 축 (area, category, menu/brand)
                     이 중 하나라도 있어야 검색 가능
        Structural : 운영 관점 제약 (주차, 발렛 등)
        Weak       : 보조 신호 (분위기, 랭킹 시그널 등)

    Args:
        raw_area, mapped_category : 정규화된 지역/카테고리
        hard_filters              : HARD_FILTER 키워드 리스트
        dietary_constraints       : 식이 제한 키워드 리스트
        soft_preferences          : SOFT_PREFERENCE 키워드 리스트
        ranking_signals           : RANKING_SIGNAL 키워드 리스트

    Returns:
        MSC 분류 결과 딕셔너리:
            msc_strong, msc_structural, msc_weak
            + mapped_category (갱신된 카테고리)
    """
    msc_strong = []       # Primary Axis (검색 가능 판단 기준)
    msc_structural = []   # Operational Constraints
    msc_weak = []         # Context / Signal / Generic

    # ── 1. Strong Signals (검색의 핵심 축) ──────
    if raw_area:
        msc_strong.append({"type": "area", "value": raw_area})

    # 도메인 일반 용어('맛집' 등)가 카테고리로 들어온 경우 격하
    is_generic_category = mapped_category in rule_engine.ontology.DOMAIN_GENERIC_TERMS
    if mapped_category and not is_generic_category:
        msc_strong.append({"type": "category", "value": mapped_category})
    elif is_generic_category:
        # 보조 마커로 격하
        msc_weak.append({"type": "generic_marker", "value": mapped_category})
        mapped_category = None

    for val in hard_filters:
        # 도메인 일반 용어가 hard_filter에 포함된 경우 weak로 격하
        if val in rule_engine.ontology.DOMAIN_GENERIC_TERMS:
            msc_weak.append({"type": "generic_marker", "value": val})
            logger.info(
                f"      -> [Audit] Hard filter '{val}' relegated to weak "
                f"(Reason: GENERIC_DOMAIN_TERM)"
            )
            continue

        # 온톨로지에서 매핑 가능한 메뉴/엔티티 → Strong
        mapped_cat = rule_engine.ontology.map_keyword(val)
        is_explicit_brand = val in [
            "맥도날드", "스타벅스", "교촌", "서브웨이", "롯데리아"
        ]

        if mapped_cat or is_explicit_brand or "점" in val:
            msc_strong.append({"type": "menu", "value": val})
        else:
            # 어느 축에도 매핑 안 되는 키워드 → weak로 격하 (오판 방지)
            msc_weak.append({"type": "unclassified_hard", "value": val})
            logger.info(
                f"      -> [Audit] Hard filter '{val}' relegated to weak "
                f"(Reason: NO_PRIMARY_AXIS)"
            )

    # ── 2. Structural Signals (운영 관점 제약) ──────
    for val in dietary_constraints:
        msc_structural.append({"type": "structural", "value": val})

    # ── 3. Weak Signals (보조 신호) ──────
    for val in soft_preferences:
        msc_weak.append({"type": "context", "value": val})
    for val in ranking_signals:
        msc_weak.append({"type": "signal", "value": val})

    return {
        "msc_strong": msc_strong,
        "msc_structural": msc_structural,
        "msc_weak": msc_weak,
        "mapped_category": mapped_category,
    }


# ═════════════════════════════════════════════
# Stage 4: 검색 vs 재질의 결정 & 페이로드 생성
# ═════════════════════════════════════════════

def _decide_and_build_payload(
    raw_area: str,
    mapped_category: str,
    msc_strong: list,
    msc_structural: list,
    msc_weak: list,
) -> dict:
    """
    MSC 분류 결과를 기반으로 SEARCH/CLARIFICATION을 결정하고
    최종 페이로드를 생성합니다.

    [결정 규칙]
        - Primary Axis(Strong)가 1개 이상 → SEARCH
        - Primary Axis가 없음 → CLARIFICATION
        - 지역만 있는 Broad Intent도 SEARCH 허용

    Args:
        raw_area, mapped_category : 검증된 지역/카테고리
        msc_strong, msc_structural, msc_weak : MSC 분류 결과

    Returns:
        결정 결과 딕셔너리:
            ui_mode, search_mode, payload, reason_type
    """
    has_primary_axis = len(msc_strong) >= 1
    is_searchable = has_primary_axis

    ui_mode = "SEARCH"
    search_mode = "FILTERED_SEARCH"
    reason_type = None
    payload = {}

    if not is_searchable:
        # ── CLARIFICATION 모드 (검색 불가) ──────
        ui_mode = "CLARIFICATION"

        # 사유 결정
        if not msc_strong and not msc_structural:
            reason_type = "ONLY_WEAK_SIGNAL"
        elif len(msc_structural) >= 1 and not has_primary_axis:
            reason_type = "OPERATIONAL_SINGLE_CONSTRAINT"
        else:
            reason_type = "NO_PRIMARY_AXIS"

        # 질문 우선순위: area > category > menu
        if not raw_area:
            primary_missing_slot = "area"
        elif not mapped_category:
            primary_missing_slot = "category"
        else:
            primary_missing_slot = "menu"

        payload = {
            "ui_mode": "CLARIFICATION",
            "primary_missing_slot": primary_missing_slot,
            "reason_type": reason_type,
            "context_ack": (
                f"{[m['value'] for m in msc_weak + msc_structural]} "
                f"조건은 확인했습니다!"
            ),
        }
    else:
        # ── SEARCH 모드 (검색 가능) ──────
        search_scope = "LOCAL" if raw_area else "GLOBAL"
        payload = {
            "ui_mode": "SEARCH",
            "search_scope": search_scope,
            "applied_filters": [
                m["value"] for m in msc_strong + msc_structural + msc_weak
            ],
            "is_global": (search_scope == "GLOBAL"),
        }

    logger.info(
        f"      -> Decision: {ui_mode} "
        f"(Reason: {reason_type}, Scope: {payload.get('search_scope')})"
    )

    return {
        "ui_mode": ui_mode,
        "search_mode": search_mode,
        "payload": payload,
        "reason_type": reason_type,
    }


# ═════════════════════════════════════════════
# 메인 노드 함수
# ═════════════════════════════════════════════

def input_parser_node(state: AgentState) -> dict:
    """
    LangGraph 그래프의 파서 노드.
    사용자 발화를 분석하여 구조화된 검색 조건을 생성합니다.

    [실행 흐름]
        1. LLM을 호출하여 슬롯(area, category, keywords) 추출
        2. JSON 파싱 및 에러 처리
        3. 지명(area) 유효성 검증 및 재분류
        4. 키워드 분류 (HARD_FILTER / SOFT_PREFERENCE / RANKING_SIGNAL)
        5. MSC 계층 분류 (Strong / Structural / Weak)
        6. SEARCH vs CLARIFICATION 결정
        7. 최종 상태 업데이트 딕셔너리 반환

    Args:
        state: 현재 AgentState

    Returns:
        상태 업데이트 딕셔너리 (LangGraph가 현재 상태에 병합)
    """
    logger.info(f"[Flow] 1. Auditing User Intent: '{state['user_input']}'")

    # ── Stage 1: LLM 호출 ──────
    behavioral_rules = rule_engine.get_node_rules("parser")
    prompt_data = _build_parser_prompt(state, behavioral_rules)

    chain = prompt_data["prompt"] | llm_extra
    response = chain.invoke(prompt_data["params"])

    try:
        # ── JSON 파싱 ──────
        content = response.content
        json_match = re.search(r"\{.*\}", response.content, re.DOTALL)
        if json_match:
            content = json_match.group(0)
        data = json.loads(content.replace("'", '"'))

        meta = data.get("meta", {})

        # ── Stage 2: 슬롯 추출 및 정규화 ──────
        raw_keywords = data.get("keywords", [])
        raw_area = sanitize_val(data.get("area"))
        mapped_category = sanitize_val(data.get("category"))

        # 지명 검증 및 비지역 토큰 재분류
        raw_area, raw_keywords = validate_area_slot(raw_area, raw_keywords)

        logger.info(f"      -> Extracted Category: {mapped_category}, Area: {raw_area}")

        # ── Stage 3: 키워드 분류 ──────
        classified = _classify_keywords(raw_keywords)

        # ── Stage 4: MSC 분류 ──────
        msc = _classify_msc(
            raw_area,
            mapped_category,
            classified["hard_filters"],
            classified["dietary_constraints"],
            classified["soft_preferences"],
            classified["ranking_signals"],
        )

        logger.info(
            f"      -> MSC Audit: Strong={msc['msc_strong']}, "
            f"Structural={msc['msc_structural']}, Weak={msc['msc_weak']}"
        )

        # 카테고리가 MSC 과정에서 갱신될 수 있음
        mapped_category = msc["mapped_category"]

        # ── Stage 5: 결정 및 페이로드 ──────
        decision = _decide_and_build_payload(
            raw_area,
            mapped_category,
            msc["msc_strong"],
            msc["msc_structural"],
            msc["msc_weak"],
        )

        ui_mode = decision["ui_mode"]
        search_mode = decision["search_mode"]

        # history_recall 의도 시 모드 오버라이드
        intent_type = meta.get("intent_type", "recommend")
        if intent_type == "history_recall":
            ui_mode = "HISTORY_RECALL"

        return {
            "chat_history": [{"role": "user", "content": state["user_input"]}],
            "area": raw_area,
            "category": mapped_category,
            "hard_filters": classified["hard_filters"],
            "soft_preferences": classified["soft_preferences"],
            "ranking_signals": classified["ranking_signals"],
            "positive_keywords": classified["positive_keywords"],
            "keyword_strengths": classified["keyword_strengths"],
            "excluded_categories": list(set(classified["excluded_categories"])),
            "excluded_names": list(set(classified["excluded_names"])),
            "negative_keywords": list(set(classified["negative_keywords"])),
            "search_mode": search_mode,
            "meta_intent": {
                "count": int(meta.get("count", 5)),
                "diversity_flag": bool(meta.get("diversity", False)),
                "ambiguity_score": 0.0,
                "intent_type": intent_type,
            },
            "clarification_needed": ui_mode == "CLARIFICATION",
            "ui_mode": ui_mode,
            "payload": decision["payload"],
            "limit": int(meta.get("count", 5)),
        }

    except Exception as e:
        # ── 에러 폴백 ──────
        # LLM 출력 파싱 실패 시 안전한 기본값을 반환합니다.
        logger.error(f"      -> Audit Failed: {e}. Content: {response.content}")
        return {
            "chat_history": [{"role": "user", "content": state["user_input"]}],
            "area": None,
            "category": None,
            "positive_keywords": [],
            "keyword_strengths": {},
            "excluded_categories": [],
            "excluded_names": [],
            "negative_keywords": [],
            "meta_intent": {
                "count": 5,
                "diversity_flag": False,
                "diversity_type": None,
                "ambiguity_score": 1.0,
                "intent_type": "recommend",
                "recall_anchor": "unspecified",
                "recall_scope": "global_session",
            },
            "inferred_categories": [],
            "clarification_needed": True,
            "clarification_options": [],
            "clarification_answer": None,
            "limit": 5,
            "ui_mode": "SEARCH",
            "relaxation_depth": 0,
            "rejection_log": [],
            "relaxation_history": [],
        }
