"""
core/nodes/generator.py — 응답 텍스트 생성 노드 (Semantic Translator)

추천 결과와 페이로드를 바탕으로 사용자에게 보여줄
자연어 응답 텍스트를 생성합니다.

[동작 모드]
    1. CLARIFICATION 모드: 정적 템플릿 기반 재질의 응답
    2. SEARCH 모드       : LLM을 사용한 추천 설명 응답

[입력]
    state["recommendations"]  : 추천 결과 리스트
    state["payload"]          : 파서가 생성한 결정 페이로드
    state["chat_history"]     : 대화 이력

[출력]
    explanation  : 최종 응답 텍스트
    chat_history : 어시스턴트 응답 추가
"""

import json

from langchain_core.prompts import ChatPromptTemplate

from core.state import AgentState
from core.llm import llm_chat
from utils.logger import get_logger
from knowledge import rule_engine

logger = get_logger("GeneratorNode")


def _render_clarification(state: AgentState) -> str:
    """
    CLARIFICATION 모드의 정적 재질의 응답을 생성합니다.

    LLM을 사용하지 않고 reason_type에 따른 사전 정의 템플릿으로
    빠르고 안정적인 응답을 반환합니다.

    Args:
        state: 현재 AgentState

    Returns:
        재질의 응답 텍스트 문자열

    템플릿 매핑:
        ONLY_WEAK_SIGNAL          → 지역 질문
        INSUFFICIENT_CONSTRAINT   → 음식 종류 질문
        MISSING_AREA              → 지역 질문
        MISSING_CATEGORY          → 메뉴 질문
    """
    payload = state.get("payload", {})
    reason_type = payload.get("reason_type")
    primary_slot = payload.get("primary_missing_slot")
    context_ack = payload.get("context_ack", "")

    logger.info(
        f"      -> Rendering CLARIFICATION "
        f"(Reason: {reason_type}, Priority: {primary_slot})"
    )

    # 사유별 응답 템플릿
    templates = {
        "ONLY_WEAK_SIGNAL": (
            f"{context_ack} 조건은 확인했습니다! "
            f"다만 이 정보만으로는 범위가 너무 넓어 정확한 추천이 어려울 수 있어요. "
            f"어느 **지역**을 위주로 찾아볼까요?"
        ),
        "INSUFFICIENT_CONSTRAINT": (
            f"{context_ack} 정보는 잘 보았습니다. "
            f"혹시 **어떤 종류의 음식**(한식, 일식 등)이나 "
            f"구체적인 메뉴를 생각 중이신가요?"
        ),
        "MISSING_AREA": (
            f"{context_ack} 맛있는 곳을 찾아드릴게요! "
            f"원하시는 **지역**(예: 강남, 홍대)을 알려주시면 "
            f"더 정확한 추천이 가능합니다."
        ),
        "MISSING_CATEGORY": (
            f"{context_ack} 근처에서 추천해 드릴게요! "
            f"혹시 어떤 **메뉴**나 분위기를 좋아하시나요?"
        ),
    }

    # 기본 템플릿 (Fallback)
    default_tpl = (
        f"{context_ack} 정보를 바탕으로 더 정확한 추천을 드리고 싶어요. "
        f"조금만 더 구체적인 정보(지역이나 음식 종류 등)를 알려주시겠어요?"
    )
    response_text = templates.get(reason_type, default_tpl)

    # primary_slot이 area인데 응답에 "지역"이 없으면 보조 안내 추가
    if primary_slot == "area" and "지역" not in response_text:
        response_text += " (어느 지역에서 찾으시는지 궁금해요!)"

    return response_text


def response_generator_node(state: AgentState) -> dict:
    """
    LangGraph 그래프의 응답 생성 노드.
    추천 결과를 사용자 친화적인 텍스트로 변환합니다.

    [실행 흐름]
        1. CLARIFICATION 모드 → 정적 템플릿 응답
        2. SEARCH 모드 → LLM을 사용하여 추천 설명 생성

    Args:
        state: 현재 AgentState

    Returns:
        상태 업데이트 딕셔너리:
            explanation  : 최종 응답 텍스트
            chat_history : 어시스턴트 응답 메시지 추가
    """
    logger.info("[Flow] 4. Generating Semantic Response (Payload Aware)")

    recs_data = state.get("recommendations", [])
    payload = state.get("payload", {})
    ui_mode = payload.get("ui_mode", "SEARCH")

    # ── [1단계] CLARIFICATION 모드 (재질의) ──────
    if ui_mode == "CLARIFICATION":
        response_text = _render_clarification(state)
        return {
            "explanation": response_text,
            "chat_history": [{"role": "assistant", "content": response_text}],
        }

    # ── [2단계] SEARCH 모드 (추천 응답 생성) ──────
    search_scope = payload.get("search_scope", "LOCAL")
    applied_filters = payload.get("applied_filters", [])

    # RULE.MD에서 생성기 행동 규칙 로드
    behavioral_rules = rule_engine.get_node_rules("generator", ui_mode=ui_mode)

    # 대화 이력 직렬화
    chat_history_str = ""
    for msg in state.get("chat_history", []):
        role = "사용자" if msg.get("role") == "user" else "봇"
        chat_history_str += f"{role}: {msg.get('content')}\n"

    # 전역 검색 시 경고 문구 추가
    global_warning = ""
    if search_scope == "GLOBAL":
        global_warning = (
            "⚠️ 현재 지역 정보가 없어 전역 기준으로 "
            "가장 좋은 곳들을 선정해 보았습니다.\n\n"
        )

    # LLM 프롬프트 구성
    prompt_template = (
        "당신은 정직한 맛집 비서입니다. "
        "아래 가이드라인과 데이터를 바탕으로 응답을 구성하세요.\n\n"
        "{behavioral_rules}\n\n"
        "[데이터]\n"
        "1. 추천 결과: {recs}\n"
        "2. 적용된 필터: {applied_filters}\n"
        "3. 검색 범위: {search_scope}\n\n"
        "[대화 문맥]\n{chat_history_str}\n\n"
        "[지침]\n"
        "- 전역 검색인 경우(GLOBAL), 반드시 응답 서두에 "
        "지역 정보 부재로 인해 전산상의 평점/인기 위주로 추천했음을 명시하세요.\n"
        "- 사용자가 제시한 필터({applied_filters})가 "
        "어떻게 반영되었는지 설명하세요.\n"
        "- 친절하고 신뢰감 있는 톤을 유지하세요.\n"
    )

    prompt = ChatPromptTemplate.from_template(prompt_template)
    chain = prompt | llm_chat

    response = chain.invoke({
        "behavioral_rules": behavioral_rules,
        "recs": json.dumps(recs_data, ensure_ascii=False, indent=2),
        "applied_filters": applied_filters,
        "search_scope": search_scope,
        "chat_history_str": chat_history_str if chat_history_str else "(없음)",
    })

    final_content = global_warning + response.content

    return {
        "explanation": final_content,
        "chat_history": [{"role": "assistant", "content": final_content}],
    }
