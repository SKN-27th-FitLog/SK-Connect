"""
core/graph.py — LangGraph StateGraph 정의 및 컴파일

맛집 추천 챗봇의 전체 워크플로우 그래프를 구성합니다.

[사용법]
    from core.graph import app_graph
    result = app_graph.invoke(initial_state, config=config)

[그래프 구조]
    parser → (clarifier | recommender)
                 ↓              ↓
             generator      validator
                            ↓
                         generator
                            ↓
                         classifier
                            ↓
                          updater
                            ↓
                    (recommender | END)

[노드 흐름]
    1. parser     : 사용자 발화 의도 파싱
    2. clarifier  : 모호한 경우 재질의 (parser → clarifier → generator)
    3. recommender: Neo4j 워터폴 검색 (parser → recommender → validator)
    4. validator  : 추천 결과 사후 검증
    5. generator  : 최종 응답 텍스트 생성
    6. classifier : 피드백 분류 (LIKE, DISLIKE, RETRY 등)
    7. updater    : 피드백에 따른 상태 업데이트 → 재추천 또는 종료

[체크포인터]
    SQLite 기반의 LangGraph 체크포인터를 사용하여
    대화 상태를 세션별로 영속적으로 저장합니다.
"""

from langgraph.graph import StateGraph, END

from core.state import AgentState
from core.nodes.parser import input_parser_node
from core.nodes.recommender import waterfall_recommend_node
from core.nodes.validator import deterministic_validator_node
from core.nodes.generator import response_generator_node
from core.nodes.clarifier import clarifier_node
from core.nodes.feedback import (
    feedback_classifier_node,
    preference_update_node,
    should_retry,
)
from database.memory import create_checkpointer


# ──────────────────────────────────────────────
# 1. 체크포인터 초기화 (팩토리 패턴 사용)
# ──────────────────────────────────────────────
# database.memory 모듈의 팩토리 함수를 통해
# SQLite 커넥션과 체크포인터를 생성합니다.
memory, _conn = create_checkpointer()


# ──────────────────────────────────────────────
# 2. StateGraph 구성
# ──────────────────────────────────────────────
workflow = StateGraph(AgentState)

# 노드 등록: 각 노드 이름은 엣지 연결 시 참조됩니다.
workflow.add_node("parser", input_parser_node)
workflow.add_node("recommender", waterfall_recommend_node)
workflow.add_node("validator", deterministic_validator_node)
workflow.add_node("generator", response_generator_node)
workflow.add_node("clarifier", clarifier_node)
workflow.add_node("classifier", feedback_classifier_node)
workflow.add_node("updater", preference_update_node)


# ──────────────────────────────────────────────
# 3. 엣지 연결 (워크플로우 흐름 정의)
# ──────────────────────────────────────────────

# 진입점: 모든 요청은 parser에서 시작
workflow.set_entry_point("parser")


def should_clarify(state: AgentState) -> str:
    """
    Parser 이후 분기 결정: 재질의가 필요하면 clarifier로,
    아니면 recommender로 라우팅합니다.

    Args:
        state: 현재 AgentState

    Returns:
        "clarifier" 또는 "recommender"

    판단 기준:
        - state["clarification_needed"]가 True이면 재질의 분기
        - 검색 가능한 Primary Axis가 있으면 추천 분기
    """
    if state.get("clarification_needed"):
        return "clarifier"
    return "recommender"


# parser → (clarifier | recommender) 분기
workflow.add_conditional_edges(
    "parser",
    should_clarify,
    {"clarifier": "clarifier", "recommender": "recommender"},
)

# clarifier → generator (재질의 응답 생성)
workflow.add_edge("clarifier", "generator")

# recommender → validator → generator (추천 파이프라인)
workflow.add_edge("recommender", "validator")
workflow.add_edge("validator", "generator")

# generator → classifier → updater (피드백 루프)
workflow.add_edge("generator", "classifier")
workflow.add_edge("classifier", "updater")

# updater → (recommender | END) 조건 분기
# 재추천이 필요하면 recommender로, 아니면 종료
workflow.add_conditional_edges(
    "updater",
    should_retry,
    {"recommender": "recommender", END: END},
)


# ──────────────────────────────────────────────
# 4. 그래프 컴파일 (체크포인터 연결)
# ──────────────────────────────────────────────
# 컴파일된 그래프는 app_graph로 export되어
# app.py에서 invoke()로 호출됩니다.
app_graph = workflow.compile(checkpointer=memory)
