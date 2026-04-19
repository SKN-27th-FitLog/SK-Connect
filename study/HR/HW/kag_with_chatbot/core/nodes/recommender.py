"""
core/nodes/recommender.py — 워터폴 검색 플래너 노드

Parser가 추출한 검색 조건을 기반으로 Neo4j에서
맛집을 검색하는 워터폴(단계적 확장) 전략을 실행합니다.

[워터폴 전략]
    Step 1: Strict Search     — 모든 조건 엄격 적용
    Step 2: Ontology Expansion — 하위어 확장 (면→[라멘,국수,...])
    Step 3: Soft Relaxation    — 키워드 조건 해제, 지역+평점 기반

[비건 전용 전략]
    Step 1: 비건 전문점 검색
    Step 2: 유의어 확장 (비건, 채식)
    Step 3: 비건 옵션 보유 식당 검색

[입력]
    state["area"], state["category"], state["hard_filters"],
    state["keyword_strengths"], state["search_mode"] 등

[출력]
    recommendations, viewed_ids, ui_mode, explanation_payload
"""

import time

from core.state import AgentState
from recommendation.engines import RecommendationEngine
from utils.logger import get_logger
from knowledge import rule_engine

logger = get_logger("RecommenderNode")


# ═════════════════════════════════════════════
# 헬퍼 함수
# ═════════════════════════════════════════════

def _merge_results(existing: list, new_results: list) -> list:
    """
    기존 결과 리스트에 신규 결과를 ID 기반으로 중복 없이 병합합니다.

    Args:
        existing   : 기존 추천 결과 리스트
        new_results: 새로 검색된 결과 리스트

    Returns:
        병합된 결과 리스트 (기존 순서 유지, 신규 항목 뒤에 추가)
    """
    existing_ids = {r["id"] for r in existing}
    for r in new_results:
        if r["id"] not in existing_ids:
            existing.append(r)
            existing_ids.add(r["id"])
    return existing


def _build_keyword_intents(hard_filters: list, soft_preferences: list,
                           keyword_strengths: dict) -> list:
    """
    검색 엔진에 전달할 keyword_intents 리스트를 구성합니다.

    hard_filters와 soft_preferences를 합치고
    각 키워드에 해당하는 강도(strength)를 부여합니다.

    Args:
        hard_filters      : HARD_FILTER 키워드 리스트
        soft_preferences  : SOFT_PREFERENCE 키워드 리스트
        keyword_strengths : 키워드별 강도 딕셔너리

    Returns:
        [{"value": "파스타", "strength": "ABSOLUTE"}, ...] 형태의 리스트
    """
    return [
        {"value": kw, "strength": keyword_strengths.get(kw, "PREFERENCE")}
        for kw in hard_filters + soft_preferences
    ]


def _run_vegan_strategy(session_id: str, area: str, keyword_intents: list,
                        ranking_signals: list, viewed_ids: list,
                        excluded_names: list, excluded_categories: list,
                        negative_keywords: list, diversity_flag: bool,
                        limit: int) -> tuple:
    """
    비건 전용 4단계 확장 검색 전략을 실행합니다.

    일반 검색과 달리 비건 식당은 DB에 매우 적을 수 있으므로
    단계별로 검색 범위를 넓혀가며 최대한 결과를 확보합니다.

    단계:
        1. 비건 전문점 (카테고리: "비건전문")
        2. 유의어 확장 (inferred: ["비건", "채식"])
        3. 비건 옵션 힌트 (keyword에 "비건옵션" 추가)

    Args:
        (표준 검색 파라미터 - 상세 생략)

    Returns:
        (results, explanation_payload_steps) 튜플
    """
    MIN_CANDIDATES = 5
    steps = []
    common_params = dict(
        session_id=session_id, area_name=area,
        keyword_intents=keyword_intents, ranking_signals=ranking_signals,
        viewed_ids=viewed_ids, excluded_names=excluded_names,
        excluded_categories=excluded_categories, negative_keywords=negative_keywords,
        diversity_flag=diversity_flag, limit=limit,
    )

    # Step 1: 비건 전문점 검색
    logger.info("      -> [Vegan Step 1] Strict Specialty Search...")
    results = RecommendationEngine.recommend_dual_constraint(
        **common_params, category_name="비건전문", is_discovery=False,
    )
    steps.append({"step": "Vegan_Strict", "count": len(results)})

    # Step 2: 유의어 확장
    if len(results) < MIN_CANDIDATES:
        logger.info("      -> [Vegan Step 2] Expanded Synonym Search...")
        syn_results = RecommendationEngine.recommend_dual_constraint(
            **common_params, category_name=None,
            inferred_categories=["비건", "채식"], is_discovery=True,
        )
        results = _merge_results(results, syn_results)
        steps.append({"step": "Vegan_Expanded", "count": len(results)})

    # Step 3: 비건 옵션 검색
    if len(results) < MIN_CANDIDATES:
        logger.info("      -> [Vegan Step 3] Option-hint Search (Non-specialty)...")
        opt_intents = keyword_intents + [{"value": "비건옵션", "strength": "PREFERENCE"}]
        opt_results = RecommendationEngine.recommend_dual_constraint(
            **common_params, category_name=None,
            keyword_intents=opt_intents, is_discovery=True,
        )
        results = _merge_results(results, opt_results)
        steps.append({"step": "Vegan_Options", "count": len(results)})

    return results, steps


def _run_standard_strategy(session_id: str, area: str, category: str,
                           hard_filters: list, keyword_intents: list,
                           ranking_signals: list, viewed_ids: list,
                           excluded_names: list, excluded_categories: list,
                           negative_keywords: list, search_mode: str,
                           diversity_flag: bool, intent_type: str,
                           limit: int) -> tuple:
    """
    일반(비비건) 3단계 워터폴 검색 전략을 실행합니다.

    단계:
        1. Strict Search     — 모든 조건 적용
        2. Ontology Expansion — 하위어 확장 (면→[라멘,...])
        3. Soft Relaxation    — 키워드 해제, 지역+평점 기반

    Args:
        (표준 검색 파라미터 - 상세 생략)

    Returns:
        (results, explanation_payload_steps) 튜플
    """
    MIN_CANDIDATES = 5
    steps = []
    common_params = dict(
        session_id=session_id, area_name=area,
        ranking_signals=ranking_signals, viewed_ids=viewed_ids,
        excluded_names=excluded_names, excluded_categories=excluded_categories,
        negative_keywords=negative_keywords,
        diversity_flag=diversity_flag, limit=limit,
    )

    # Step 1: 엄격 검색
    logger.info("      -> [Step 1] Attempting Strict Search...")
    results = RecommendationEngine.recommend_dual_constraint(
        **common_params, category_name=category,
        keyword_intents=keyword_intents,
        is_discovery=(search_mode == "DISCOVERY"),
    )
    steps.append({"step": "Strict", "count": len(results)})

    # Step 2: 온톨로지 확장 (결과 부족 시)
    if len(results) < MIN_CANDIDATES and intent_type != "history_recall":
        logger.info(
            f"      -> [Step 2] Result ({len(results)}) < {MIN_CANDIDATES}. "
            f"Attempting Ontology Expansion..."
        )
        expanded_inferred = []
        for kw in hard_filters:
            hyponyms = rule_engine.ontology.HYPONYM_MAP.get(kw, [])
            safe_hyponyms = [
                h for h in hyponyms
                if h not in negative_keywords and h not in excluded_categories
            ]
            expanded_inferred.extend(safe_hyponyms)

        if expanded_inferred:
            expanded_results = RecommendationEngine.recommend_dual_constraint(
                **common_params, category_name=category,
                inferred_categories=list(set(expanded_inferred)),
                keyword_intents=keyword_intents, is_discovery=True,
            )
            results = _merge_results(results, expanded_results)
            steps.append({"step": "Expanded", "count": len(results)})

    # Step 3: 소프트 완화 (여전히 부족 시)
    if len(results) < MIN_CANDIDATES and intent_type != "history_recall":
        logger.info(
            f"      -> [Step 3] Result ({len(results)}) still < {MIN_CANDIDATES}. "
            f"Attempting Soft Relaxation..."
        )
        relaxed_results = RecommendationEngine.recommend_dual_constraint(
            **common_params, category_name=None,
            keyword_intents=[], is_discovery=True,
        )
        results = _merge_results(results, relaxed_results)
        steps.append({"step": "Relaxed", "count": len(results)})

    return results, steps


# ═════════════════════════════════════════════
# 메인 노드 함수
# ═════════════════════════════════════════════

def waterfall_recommend_node(state: AgentState) -> dict:
    """
    LangGraph 그래프의 추천 노드.
    워터폴 전략으로 Neo4j에서 맛집을 검색합니다.

    [실행 흐름]
        1. CLARIFICATION 모드면 검색 우회 (빈 결과 반환)
        2. 비건 요청이면 비건 전용 전략 실행
        3. 일반 요청이면 3단계 워터폴 전략 실행
        4. 결과가 0개면 CLARIFICATION 모드로 전환
        5. 추천 히스토리 기록 및 viewed_ids 업데이트

    Args:
        state: 현재 AgentState

    Returns:
        상태 업데이트 딕셔너리:
            recommendations, viewed_ids, ui_mode, explanation_payload
    """
    session_id = state["session_id"]
    viewed_ids = state.get("viewed_ids", [])
    limit = state.get("limit", 10)

    category = state.get("category")
    area = state.get("area")
    hard_filters = state.get("hard_filters", [])
    soft_preferences = state.get("soft_preferences", [])
    ranking_signals = state.get("ranking_signals", [])
    keyword_strengths = state.get("keyword_strengths", {})

    excluded_names = state.get("excluded_names", [])
    excluded_categories = state.get("excluded_categories", [])
    negative_keywords = state.get("negative_keywords", [])

    search_mode = state.get("search_mode", "FILTERED_SEARCH")
    ui_mode = state.get("ui_mode", "SEARCH")
    meta_intent = state.get("meta_intent", {})
    intent_type = meta_intent.get("intent_type", "recommend")
    diversity_flag = meta_intent.get("diversity_flag", False)
    dietary_constraints = state.get("dietary_constraints", [])

    logger.info(f"[Flow] 2. Waterfall Search (Mode: {search_mode}, Intent: {intent_type})")

    # ── CLARIFICATION 우회 ──────
    if ui_mode == "CLARIFICATION":
        logger.info("      -> [Bypass] Parser already triggered CLARIFICATION. Skipping search.")
        return {
            "recommendations": [],
            "ui_mode": "CLARIFICATION",
            "explanation_payload": {"steps": [], "final_strategy": "BYPASS_CLARIFICATION"},
        }

    # ── 키워드 인텐트 구성 ──────
    keyword_intents = _build_keyword_intents(hard_filters, soft_preferences, keyword_strengths)

    # ── 전략 실행 (비건 vs 일반) ──────
    if "비건" in dietary_constraints:
        logger.info("      -> [Vegan Strategy] 4-Step Expansion triggered for 'Vegan'.")
        results, steps = _run_vegan_strategy(
            session_id, area, keyword_intents, ranking_signals,
            viewed_ids, excluded_names, excluded_categories,
            negative_keywords, diversity_flag, limit,
        )
    else:
        results, steps = _run_standard_strategy(
            session_id, area, category, hard_filters, keyword_intents,
            ranking_signals, viewed_ids, excluded_names, excluded_categories,
            negative_keywords, search_mode, diversity_flag, intent_type, limit,
        )

    explanation_payload = {"steps": steps, "final_strategy": None}

    # ── 최종 검증 및 히스토리 기록 ──────
    if not results:
        logger.warning("      -> [Waterfall Result] Zero results across all steps. Triggering Clarification.")
        ui_mode = "CLARIFICATION"
    else:
        rec_names = [r.get("name") for r in results[:limit]]
        logger.info(f"      -> [Waterfall Result] Success! Finalizing with {len(results)} candidates.")
        logger.info(f"      -> [Final Recs] {rec_names}")

        # 추천 히스토리 저장 (컨텍스트 회상에 활용)
        chat_history = state.get("chat_history", [])
        turn_index = len([msg for msg in chat_history if msg["role"] == "user"])
        new_record = {
            "turn_index": turn_index,
            "category": category,
            "ids": [r["id"] for r in results if r.get("id")],
            "intent_snapshot": {"search_mode": search_mode, "steps": steps},
            "timestamp": time.time(),
        }
        state.get("recommendation_records", []).append(new_record)

    # viewed_ids 업데이트 (중복 제거, 순서 유지)
    new_viewed_ids = viewed_ids + [r["id"] for r in results if r.get("id")]

    return {
        "recommendations": results[:limit],
        "viewed_ids": list(dict.fromkeys(new_viewed_ids)),
        "ui_mode": ui_mode,
        "explanation_payload": explanation_payload,
    }
