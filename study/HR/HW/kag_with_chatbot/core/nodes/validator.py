"""
core/nodes/validator.py — 추천 결과 사후 검증 노드

Recommender가 반환한 추천 결과가 사용자의 제약 조건
(HARD_NEGATIVE, ABSOLUTE)을 위반하지 않는지 강제 검증합니다.

[검증 규칙]
    A. HARD_NEGATIVE: 제외 카테고리/이름이 포함된 결과 탈락
    B. ABSOLUTE:      필수 키워드가 없는 결과 탈락

[Fail-safe]
    모든 결과가 ABSOLUTE 위반으로 탈락하면
    RELAXATION_PROPOSAL 모드로 전환하여
    사용자에게 완화 제안을 합니다.

[입력]
    state["recommendations"]     : 추천 결과 리스트
    state["keyword_intent"]      : 키워드 인텐트 (강도 포함)
    state["excluded_categories"] : 제외 카테고리
    state["excluded_names"]      : 제외 식당명

[출력]
    recommendations : 검증 통과한 결과만 남긴 리스트
    rejection_log   : 탈락 사유 로그
    ui_mode         : 필요 시 RELAXATION_PROPOSAL로 전환
"""

from core.state import AgentState
from utils.logger import get_logger

logger = get_logger("ValidatorNode")


def _validate_hard_negative(rec: dict, excluded_categories: list,
                            excluded_names: list) -> dict:
    """
    개별 추천 항목이 HARD_NEGATIVE 제약을 위반하는지 검사합니다.

    HARD_NEGATIVE는 "~말고", "~빼고" 같은 절대 제외 조건입니다.
    카테고리명이나 식당명에 제외 대상이 포함되어 있으면 탈락시킵니다.

    Args:
        rec                 : 검증할 추천 항목 딕셔너리
        excluded_categories : 제외 카테고리 리스트 (예: ["중식"])
        excluded_names      : 제외 식당명 리스트

    Returns:
        위반 시: {"rejected": True, "rule_id": "HARD_NEGATIVE", "reason": "..."}
        통과 시: {"rejected": False}
    """
    rec_category = str(rec.get("category", "") or "")
    rec_name = rec.get("name", "Unknown")

    for exc_cat in excluded_categories:
        if exc_cat in rec_category or exc_cat in rec_name:
            return {
                "rejected": True,
                "rule_id": "HARD_NEGATIVE",
                "reason": f"Excluded category '{exc_cat}' matched",
            }

    for exc_name in excluded_names:
        if exc_name in rec_name:
            return {
                "rejected": True,
                "rule_id": "HARD_NEGATIVE",
                "reason": f"Excluded name '{exc_name}' matched",
            }

    return {"rejected": False}


def _validate_absolute_keywords(rec: dict, absolute_kws: list) -> dict:
    """
    개별 추천 항목이 ABSOLUTE 키워드 제약을 충족하는지 검사합니다.

    ABSOLUTE는 양보 불가능한 필수 조건입니다.
    상호명이나 카테고리에 해당 키워드가 전혀 없으면 탈락시킵니다.

    Args:
        rec          : 검증할 추천 항목 딕셔너리
        absolute_kws : 필수 키워드 리스트

    Returns:
        위반 시: {"rejected": True, "rule_id": "ABSOLUTE_KEYWORD_VIOLATION", "reason": "..."}
        통과 시: {"rejected": False}
    """
    rec_name = rec.get("name", "Unknown")
    rec_category = str(rec.get("category", "") or "")

    for abs_kw in absolute_kws:
        if abs_kw not in rec_name and abs_kw not in rec_category:
            return {
                "rejected": True,
                "rule_id": "ABSOLUTE_KEYWORD_VIOLATION",
                "reason": f"Missing mandatory keyword '{abs_kw}'",
            }

    return {"rejected": False}


def deterministic_validator_node(state: AgentState) -> dict:
    """
    LangGraph 그래프의 검증 노드.
    추천 결과를 HARD_NEGATIVE 및 ABSOLUTE 제약 기준으로 필터링합니다.

    [실행 흐름]
        1. ABSOLUTE 키워드 추출
        2. 각 추천 항목에 대해 HARD_NEGATIVE 검증
        3. 통과한 항목에 대해 ABSOLUTE 키워드 검증
        4. 모든 항목 탈락 + ABSOLUTE 위반이 지배적 → RELAXATION_PROPOSAL
        5. 검증 리포트 생성

    Args:
        state: 현재 AgentState

    Returns:
        상태 업데이트 딕셔너리:
            recommendations     : 검증 통과한 결과 리스트
            rejection_log       : 탈락 로그 (기존 로그에 누적)
            explanation_payload : 검증 요약 정보
            ui_mode             : 필요 시 RELAXATION_PROPOSAL
    """
    logger.info("[Flow] 3. Validating Results (Strict Enforcement)")

    recommendations = state.get("recommendations", [])
    keyword_intent = state.get("keyword_intent", [])
    excluded_categories = state.get("excluded_categories", [])
    excluded_names = state.get("excluded_names", [])

    # ABSOLUTE 키워드 추출 (양보 불가 필수 조건)
    absolute_kws = [
        k["value"] for k in keyword_intent if k.get("strength") == "ABSOLUTE"
    ]

    rejection_log = []
    pure_recommendations = []
    violation_summary = {"dominant_rule": None, "count": 0}

    for rec in recommendations:
        rec_id = rec.get("id")
        rec_name = rec.get("name", "Unknown")

        # ── A. HARD_NEGATIVE 검증 ──────
        hn_result = _validate_hard_negative(rec, excluded_categories, excluded_names)
        if hn_result["rejected"]:
            rejection_log.append({
                "item_id": rec_id, "name": rec_name,
                "rule_id": hn_result["rule_id"], "reason": hn_result["reason"],
            })
            violation_summary["dominant_rule"] = "HARD_NEGATIVE"
            violation_summary["count"] += 1
            logger.warning(f"      -> Rejected '{rec_name}' due to HARD_NEGATIVE")
            continue

        # ── B. ABSOLUTE 키워드 검증 ──────
        abs_result = _validate_absolute_keywords(rec, absolute_kws)
        if abs_result["rejected"]:
            rejection_log.append({
                "item_id": rec_id, "name": rec_name,
                "rule_id": abs_result["rule_id"], "reason": abs_result["reason"],
            })
            violation_summary["dominant_rule"] = "ABSOLUTE_KEYWORD"
            violation_summary["count"] += 1
            logger.warning(f"      -> Rejected '{rec_name}' due to ABSOLUTE_KEYWORD")
            continue

        # 검증 통과
        pure_recommendations.append(rec)

    # ── ABSOLUTE 위반으로 전멸 시 완화 제안 모드 전환 ──────
    ui_mode = state.get("ui_mode", "SEARCH")
    if (not pure_recommendations
            and violation_summary["dominant_rule"] == "ABSOLUTE_KEYWORD"):
        logger.info(
            "      -> ABSOLUTE keyword failure detected. "
            "Triggering RELAXATION_PROPOSAL."
        )
        ui_mode = "RELAXATION_PROPOSAL"

    # ── 검증 리포트 생성 ──────
    explanation_payload = {
        "summary_reason": (
            f"{violation_summary['count']}개의 결과가 엄격한 제약"
            f"(제외 조건 또는 필수 키워드) 위반으로 제외되었습니다."
            if violation_summary["count"] > 0 else None
        ),
        "dominant_rule": violation_summary["dominant_rule"],
        "has_results": len(pure_recommendations) > 0,
    }

    if pure_recommendations:
        logger.info(
            f"      -> Validation Success: {len(pure_recommendations)} candidates passed. "
            f"Final: {[r.get('name') for r in pure_recommendations]}"
        )
    else:
        logger.warning("      -> Validation Failed: All candidates were filtered out.")

    return {
        "rejection_log": state.get("rejection_log", []) + rejection_log,
        "recommendations": pure_recommendations,
        "explanation_payload": explanation_payload,
        "ui_mode": ui_mode,
    }
