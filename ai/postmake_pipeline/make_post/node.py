import time
from typing import Optional, TypedDict

from common.logging_config import set_logging
from langgraph.graph import END, START, StateGraph
from make_post.evaluation import evaluate_post_completion
from make_post.generation import (
    MAX_REGENERATION_COUNT,
    make_post,
    make_title,
    regenerate_post,
)

logger = set_logging()


class State(TypedDict):
    """LangGraph 노드들이 공유하는 게시글 생성 상태."""
    keyword: list[str]
    keyword_stats: Optional[list[dict]]
    negative_keywords: Optional[list[str]]
    data: list[dict]
    post: Optional[str]
    title: Optional[str]
    reason: Optional[str]
    sample_data: Optional[dict | list[dict]]
    image_list: Optional[list]
    source_facts: Optional[str]
    is_pass: Optional[bool]
    retry_count: int


def evaluate_post(state: State) -> State:
    """완성된 게시글이 저장 가능한 품질인지 검사한다."""
    try:
        first_row = state["data"][0] if state.get("data") else {}
        logger.info(f"evaluate_post start | shop_id={first_row.get('shop_id')}")

        result = evaluate_post_completion(state)
        logger.info(
            f"evaluate_post end | shop_id={first_row.get('shop_id')} | "
            f"is_pass={result.get('is_pass')} | reason={result.get('reason')}"
        )
        if not result.get("is_pass"):
            logger.warning(
                f"post evaluation failed | shop_id={first_row.get('shop_id')} | "
                f"retry_count={state.get('retry_count', 0)} | reason={result.get('reason')}"
            )

        return {
            **state,
            "is_pass": result.get("is_pass"),
            "reason": result.get("reason"),
        }

    except Exception as e:
        first_row = state["data"][0] if state.get("data") else {}
        logger.error(
            f"evaluate_post failed | Error={e} | time={time.time()} | "
            f"crawling_id={first_row.get('crawling_id')}"
        )
        return state


def route_after_evaluation(state: State) -> str:
    """평가 통과 또는 최대 재시도 도달 시 그래프를 종료한다."""
    if state.get("is_pass"):
        return "make_title"
    if state.get("retry_count", 0) >= MAX_REGENERATION_COUNT:
        return "end"
    return "regenerate_post"


def build_graph():
    """게시글 생성부터 평가까지의 LangGraph 흐름을 구성한다."""
    graph = StateGraph(State)
    graph.add_node("make_post", make_post)
    graph.add_node("make_title", make_title)
    graph.add_node("regenerate_post", regenerate_post)
    graph.add_node("evaluate_post", evaluate_post)
    graph.add_edge(START, "make_post")
    graph.add_edge("make_post", "evaluate_post")
    graph.add_edge("regenerate_post", "evaluate_post")
    graph.add_edge("make_title", END)

    # 평가를 통과한 본문에만 제목을 만들고, 실패 시 최대 retry_count까지 재생성한다.
    graph.add_conditional_edges(
        "evaluate_post",
        route_after_evaluation,
        {
            "make_title": "make_title",
            "regenerate_post": "regenerate_post",
            "end": END,
        },
    )
    return graph.compile()


graph = build_graph()
