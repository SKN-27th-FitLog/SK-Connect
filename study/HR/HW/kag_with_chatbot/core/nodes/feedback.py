"""
core/nodes/feedback.py — 피드백 분류 및 선호도 업데이트 노드

사용자의 좋아요/싫어요 피드백과 완화 축 선택을 처리합니다.

[포함 노드]
    1. feedback_classifier_node : 피드백 텍스트 → 유형 분류
    2. preference_update_node   : 분류된 피드백에 따른 상태 업데이트
    3. should_retry              : 재추천 루프 분기 결정

[피드백 유형]
    LIKE            : 특정 식당 좋아요 → 선호도 학습
    DISLIKE         : 특정 식당 싫어요 → 제외 대상 추가
    RETRY           : 다른 결과 요청
    RELAX_KEYWORD   : 키워드 조건 완화 후 재검색
    EXPAND_CATEGORY : 카테고리 범위 확장 후 재검색
    EXPAND_RADIUS   : 검색 반경 확장 후 재검색
    START_OVER      : 모든 조건 초기화
"""

from langgraph.graph import END
from langchain_core.prompts import ChatPromptTemplate

from core.state import AgentState
from core.llm import llm_extra
from utils.logger import get_logger

logger = get_logger("FeedbackNode")


def feedback_classifier_node(state: AgentState) -> dict:
    """
    사용자의 피드백 텍스트를 분석하여 피드백 유형을 결정합니다.

    [분류 전략]
        1단계: 규칙 기반 키워드 매칭 (빠르고 정확)
            - "메뉴 포기", "RELAX_KW" → RELAX_KEYWORD
            - "다른 카테고리", "EXPAND_CAT" → EXPAND_CATEGORY
            - "반경 확장", "EXPAND_RAD" → EXPAND_RADIUS
            - "다시 시작", "START_OVER" → START_OVER

        2단계: LLM 기반 분류 (규칙으로 판단 불가능한 경우)
            - LLM이 LIKE, DISLIKE, RETRY, START_OVER, NONE 중 결정

    Args:
        state: 현재 AgentState (feedback_content 사용)

    Returns:
        {"feedback_type": "분류 결과"}
    """
    content = state.get("feedback_content")
    if not content:
        return {"feedback_type": "NONE"}

    logger.info(f"\n[Flow] 4. Classifying Feedback: '{content}'")

    # ── 1단계: 규칙 기반 키워드 매칭 (우선) ──────
    relax_keywords = ["메뉴 포기", "메뉴 제외", "키워드 완화", "RELAX_KW"]
    if any(kw in content for kw in relax_keywords):
        return {"feedback_type": "RELAX_KEYWORD"}

    expand_cat_keywords = ["다른 카테고리", "범위 넓히기", "EXPAND_CAT"]
    if any(kw in content for kw in expand_cat_keywords):
        return {"feedback_type": "EXPAND_CATEGORY"}

    expand_rad_keywords = ["반경 확장", "더 멀리", "EXPAND_RAD"]
    if any(kw in content for kw in expand_rad_keywords):
        return {"feedback_type": "EXPAND_RADIUS"}

    if "다시 시작" in content or "START_OVER" in content:
        return {"feedback_type": "START_OVER"}

    # ── 2단계: LLM 기반 분류 (Fallback) ──────
    prompt = ChatPromptTemplate.from_template(
        "사용자의 피드백을 분석하여 다음 중 하나로 분류하세요: "
        "['LIKE', 'DISLIKE', 'RETRY', 'START_OVER', 'NONE']\n"
        "피드백: {feedback_content}\n"
        "결과는 반드시 대문자 단어 하나로만 답하세요."
    )
    chain = prompt | llm_extra
    response = chain.invoke({"feedback_content": content})

    return {"feedback_type": response.content.strip().upper()}


def preference_update_node(state: AgentState) -> dict:
    """
    분류된 피드백 유형에 따라 검색 상태를 업데이트합니다.

    [완화 축별 동작]
        RELAX_KEYWORD   : keyword_intent 초기화 → 키워드 없이 재검색
        EXPAND_CATEGORY : category를 None으로 → 전체 카테고리 검색
        EXPAND_RADIUS   : area를 None으로 → 전역 검색
        START_OVER      : 모든 조건 초기화 (깨끗한 상태)

    Args:
        state: 현재 AgentState (feedback_type 사용)

    Returns:
        상태 업데이트 딕셔너리 (해당 필드만 변경)
    """
    fb_type = state.get("feedback_type")
    updates = {}

    if fb_type == "RELAX_KEYWORD":
        logger.info("      -> Relaxing Keywords. Clearing keyword_intent.")
        updates["keyword_intent"] = []
        updates["ui_mode"] = "SEARCH"
        updates["relaxation_depth"] = state.get("relaxation_depth", 0) + 1

    elif fb_type == "EXPAND_CATEGORY":
        logger.info("      -> Expanding Category to adjacent tags.")
        # 카테고리를 해제하여 전체 검색 유도
        updates["category"] = None
        updates["ui_mode"] = "SEARCH"
        updates["relaxation_depth"] = state.get("relaxation_depth", 0) + 1

    elif fb_type == "EXPAND_RADIUS":
        logger.info("      -> Expanding Radius. Clearing area constraint.")
        # 지역 조건을 해제하여 전역 검색
        updates["area"] = None
        updates["ui_mode"] = "SEARCH"
        updates["relaxation_depth"] = state.get("relaxation_depth", 0) + 1

    elif fb_type == "START_OVER":
        logger.info("      -> Starting Over. Resetting all constraints.")
        updates["relaxation_depth"] = 0
        updates["ui_mode"] = "SEARCH"
        updates["keyword_intent"] = []
        updates["category"] = None
        updates["area"] = None
        updates["rejection_log"] = []

    return updates


def should_retry(state: AgentState) -> str:
    """
    재추천 루프 분기 결정 함수.
    LangGraph의 conditional_edges에서 사용됩니다.

    재추천이 필요한 피드백 유형:
        RETRY, RELAX_KEYWORD, EXPAND_CATEGORY,
        EXPAND_RADIUS, START_OVER

    Args:
        state: 현재 AgentState

    Returns:
        "recommender" (재추천) 또는 END (종료)
    """
    fb_type = state.get("feedback_type")
    retry_types = [
        "RETRY", "RELAX_KEYWORD", "EXPAND_CATEGORY",
        "EXPAND_RADIUS", "START_OVER",
    ]
    if fb_type in retry_types:
        return "recommender"
    return END
