"""
core/nodes/clarifier.py — 재질의(Clarification) 판단 노드

사용자의 의도가 모호하거나 광의의 키워드(면, 고기 등)를
사용한 경우 재질의가 필요한지 판단합니다.

[트리거 조건]
    1. ambiguity_score > 0.6 (높은 모호도)
    2. 광의 키워드가 3개 이상 카테고리에 걸치는 경우
    3. diversity_flag=True이지만 type이 미지정인 경우

[출력]
    clarification_needed가 True이면:
        → 사용자에게 선택지(options)를 제공
    False이면:
        → 기본 다양성 타입(CATEGORY)을 자동 할당
"""

import logging
from typing import Dict, List, Optional, Any

from core.state import AgentState
from knowledge import rule_engine

logger = logging.getLogger("ClarifierNode")


def _check_broad_keywords(positive_keywords: list) -> tuple:
    """
    긍정 키워드 중 광의 의도(Broad Intent)에 해당하는 것을 감지합니다.

    예: "면" → [한식, 일식, 양식, 아시아음식, 중식] (5개 카테고리)
    3개 이상 카테고리에 걸치면 재질의 트리거.

    Args:
        positive_keywords: 파서가 추출한 긍정 키워드 리스트

    Returns:
        (need_clarification, reasons, inferred_categories) 튜플
        - need_clarification : 재질의 필요 여부
        - reasons            : 트리거 사유 리스트
        - inferred_categories: 감지된 후보 카테고리 목록
    """
    need_clarification = False
    reasons = []
    inferred_categories = []

    for kw in positive_keywords:
        cats = rule_engine.ontology.get_broad_categories(kw)
        if cats:
            inferred_categories.extend(cats)
            # 3개 이상 카테고리에 걸칠 정도로 광범위한 키워드
            if len(cats) >= 3:
                need_clarification = True
                reasons.append(
                    f"Broad keyword detected: '{kw}' ({len(cats)} candidates)"
                )

    return need_clarification, reasons, inferred_categories


def _build_clarification_options() -> list:
    """
    재질의 시 사용자에게 제시할 다양성 선택지를 생성합니다.

    Returns:
        ClarificationOption 형태의 딕셔너리 리스트:
            A: 카테고리 다양성 (한식/일식/양식 골고루)
            B: 맛/메뉴 특징 다양성 (매콤/담백/특별 메뉴)
            C: 분위기/환경 다양성 (조용/활기/가성비)
    """
    return [
        {
            "id": "A",
            "label": "카테고리 다양성",
            "description": "한식, 일식, 양식 등 다양한 종류의 식당을 골고루 보여드릴까요?",
        },
        {
            "id": "B",
            "label": "맛/메뉴 특징 다양성",
            "description": "매콤한 맛, 담백한 맛, 특별한 메뉴 등 맛의 특징이 다양한 곳을 보여드릴까요?",
        },
        {
            "id": "C",
            "label": "분위기/환경 다양성",
            "description": "조용한 곳, 활기찬 곳, 가성비 좋은 곳 등 분위기가 다양한 곳을 보여드릴까요?",
        },
    ]


def clarifier_node(state: AgentState) -> dict:
    """
    LangGraph 그래프의 재질의 판단 노드.
    사용자 의도의 모호성을 평가하고 필요 시 선택지를 제공합니다.

    [트리거 평가 순서]
        1. ambiguity_score 임계값 체크 (> 0.6)
        2. 광의 키워드 감지 (면, 고기 등)
        3. diversity_flag + type 미지정 조합

    Args:
        state: 현재 AgentState

    Returns:
        상태 업데이트 딕셔너리:
            clarification_needed 가 True이면:
                → ui_mode="CLARIFICATION", options 제공
            False이면:
                → diversity_type 자동 할당 (기본: CATEGORY)
    """
    meta = state.get("meta_intent", {})
    ambiguity_score = meta.get("ambiguity_score", 0.0)
    positive_keywords = state.get("positive_keywords", [])
    diversity_flag = meta.get("diversity_flag", False)
    diversity_type = meta.get("diversity_type")

    AMBIGUITY_THRESHOLD = 0.6
    clarification_needed = False
    reasons = []

    # ── Trigger 1: 높은 모호도 점수 ──────
    if ambiguity_score > AMBIGUITY_THRESHOLD:
        clarification_needed = True
        reasons.append(f"High ambiguity score: {ambiguity_score}")

    # ── Trigger 2: 광의 키워드 감지 ──────
    broad_needed, broad_reasons, inferred_categories = _check_broad_keywords(
        positive_keywords
    )
    if broad_needed:
        clarification_needed = True
        reasons.extend(broad_reasons)

    # ── Trigger 3: 다양성 요청이지만 유형 미지정 ──────
    if diversity_flag and diversity_type is None:
        clarification_needed = True
        reasons.append("Diversity requested without specific type")

    # ── 결과 반환 ──────
    if clarification_needed:
        logger.info(f"[Flow] 1.5 Clarification Triggered. Reasons: {reasons}")
        return {
            "clarification_needed": True,
            "ui_mode": "CLARIFICATION",
            "clarification_options": _build_clarification_options(),
            "inferred_categories": list(set(inferred_categories)),
        }
    else:
        # 재질의 불필요 → 기본 다양성 타입 자동 할당
        logger.info("      -> Clarification not required. Defaulting to Category Diversity.")
        new_meta = meta.copy()
        if diversity_flag and not diversity_type:
            new_meta["diversity_type"] = "CATEGORY"

        return {
            "clarification_needed": False,
            "meta_intent": new_meta,
            "inferred_categories": list(set(inferred_categories)),
        }
