from langgraph.graph import StateGraph, START, END
from langchain_huggingface import HuggingFaceEmbeddings
from typing import TypedDict
from common.logging_config import set_logging
from common.connection import Connection, PGVectorStore
from make_post.evaluation import evaluate_post_completion
from common.llm_factory import get_llm
from typing import Optional
from get_data.get_another import get_similar_post
from common.prompt import Create_Prompt
from get_data.get_another import get_image
import time
import os
import random

logger = set_logging()


def get_embeddings():
    model = HuggingFaceEmbeddings(
        model_name='sentence-transformers/all-mpnet-base-v2',
        model_kwargs={
            "token": os.getenv("HF_TOKEN"),
        },
    )
    return model

def get_vectorstore():
    return PGVectorStore().get_vectorstore()

def get_connection():
    return Connection().get_connection()


def _extract_image_urls(image_list: Optional[list]) -> list[str]:
    """DB 조회 결과 또는 문자열 목록에서 실제 이미지 URL만 추출한다."""
    urls = []
    for image in image_list or []:
        url = None
        if isinstance(image, dict):
            url = image.get('image_url') or image.get('url')
        elif image is not None:
            url = str(image)
        if url:
            urls.append(str(url))
    return urls


def _ensure_media(post: str, image_list: Optional[list], url: Optional[str]) -> str:
    """LLM 응답에 이미지 URL과 원문 URL이 빠졌으면 본문 끝에 보강한다."""
    content = str(post or "").strip()
    image_urls = _extract_image_urls(image_list)
    if image_urls and not any(image_url in content for image_url in image_urls):
        content = f"{content}\n\n{image_urls[0]}"
    if url and str(url) not in content:
        content = f"{content}\n\n{url}"
    return content


"""===================================================================="""


class State(TypedDict):
    """LangGraph 노드들이 공유하는 게시글 생성 상태."""
    keyword: list[str]
    keyword_stats: Optional[list[dict]]
    negative_keywords: Optional[list[str]]
    data: list[dict]
    post: Optional[str]
    title: Optional[str]
    similar_post: Optional[list[str]]
    reason: Optional[str]
    sample_data: Optional[dict]
    is_pass: Optional[bool]
    retry_count: int


def make_post(state: State) -> State:
    """키워드, 이미지, 샘플 analysis row를 기반으로 게시글 초안을 만든다."""
    try:
        logger.info(f"make_post start | shop_id={state['data'][0].get('shop_id')}")
        llm = get_llm()
        image_list = get_image(state['data'])

        # 여러 리뷰 중 하나를 샘플로 골라 프롬프트에 넣어 게시글의 구체성을 높인다.
        sample_data = None
        url = None
        if state['data']:
            sample_data = random.choice(state['data'])
            url = state['data'][0].get('article_url')
        if sample_data:
            url = sample_data.get('article_url')
        prompt = Create_Prompt.get_prompt(
            state['keyword'],
            image_list,
            url,
            sample_data,
            state.get('keyword_stats'),
            state.get('negative_keywords'),
        )
        response = llm.invoke(prompt)
        post = str(response)
        if hasattr(response, "content"):
            post = response.content
        post = _ensure_media(post, image_list, url)
        logger.info(f"make_post end | shop_id={state['data'][0].get('shop_id')} | post_len={len(post)}")
        
        return {
            **state,
            'post': post,
            'sample_data': sample_data,
        }
    except Exception as e:
        logger.error(f"Error={e} | time={time.time()} | crawling_id={state['data'][0].get('crawling_id')}")
        return {
            **state,
            'retry_count': state.get('retry_count', 0) + 1,
        }

def make_title(state: State) -> State:
    """생성된 게시글 본문을 바탕으로 제목을 만든다."""
    try:
        logger.info(f"make_title start | shop_id={state['data'][0].get('shop_id')}")
        llm = get_llm()
        prompt = Create_Prompt.get_title_prompt(state['post'])
        response = llm.invoke(prompt)
        title = str(response)
        if hasattr(response, "content"):
            title = response.content
        logger.info(f"make_title end | shop_id={state['data'][0].get('shop_id')} | title_len={len(title)}")
        return {
            **state,
            'title': title,
        }
    except Exception as e:
        logger.error(f"Error={e} | time={time.time()} | crawling_id={state['data'][0].get('crawling_id')}")
        return state

def embedding(state: State, similarity_distance_threshold: float = 0.25) -> State:
    """생성 게시글과 기존 벡터 문서의 유사도를 조회한다."""
    try:
        logger.info(f"embedding start | shop_id={state['data'][0].get('shop_id')}")
        vectorstore = get_vectorstore()
        results = vectorstore.similarity_search_with_score(state['post'], k=5)

        # PGVector cosine score는 distance라서 값이 낮을수록 기존 글과 더 유사하다.
        similar_results = [
            document
            for document, score in results
            if score <= similarity_distance_threshold
        ]
        state['similar_post'] = None
        if similar_results:
            state['similar_post'] = get_similar_post(similar_results)
        best_score = min((score for _, score in results), default=None)
        logger.info(
            f"embedding end | shop_id={state['data'][0].get('shop_id')} | "
            f"similar_count={len(state.get('similar_post') or [])} | best_score={best_score}"
        )
        return state
    except Exception as e:
        logger.error(f"Error={e} | time={time.time()} | crawling_id={state['data'][0].get('crawling_id')}")
        return state

def regenerate_post(state: State) -> State:
    """평가 실패 사유 또는 유사 게시글을 반영해 게시글을 다시 생성한다."""
    try:
        retry_count = state.get('retry_count', 0)
        if retry_count >= 2:
            return state
        logger.info(f"regenerate_post start | shop_id={state['data'][0].get('shop_id')} | retry_count={retry_count}")
        llm = get_llm()
        image_list = get_image(state['data'])
        sample_data = state.get('sample_data')
        url = None
        if not sample_data and state['data']:
            sample_data = random.choice(state['data'])
        if state['data']:
            url = state['data'][0].get('article_url')
        if sample_data:
            url = sample_data.get('article_url')

        # 실패 사유가 있으면 품질 보정 프롬프트를, 유사 게시글이 있으면 중복 회피 프롬프트를 우선한다.
        prompt = Create_Prompt.get_prompt(
            state['keyword'],
            image_list,
            url,
            sample_data,
            state.get('keyword_stats'),
            state.get('negative_keywords'),
        )
        if state['similar_post']:
            prompt = Create_Prompt.get_regenerate_prompt(
                state['similar_post'],
                state['keyword'],
                image_list,
                url,
                sample_data,
                state.get('keyword_stats'),
                state.get('negative_keywords'),
            )
        if state['reason']:
            prompt = Create_Prompt.get_regenerate_reason_prompt(
                state['reason'],
                state['keyword'],
                image_list,
                url,
                sample_data,
                state.get('keyword_stats'),
                state.get('negative_keywords'),
            )
        response = llm.invoke(prompt)
        post = str(response)
        if hasattr(response, "content"):
            post = response.content
        post = _ensure_media(post, image_list, url)
        logger.info(f"regenerate_post end | shop_id={state['data'][0].get('shop_id')} | retry_count={retry_count + 1} | post_len={len(post)}")
        return {
            **state,
            'post': post,
            'sample_data': sample_data,
            'similar_post': None,
            'reason': None,
            'is_pass': None,
            'retry_count': retry_count + 1,
        }
    except Exception as e:
        logger.error(f"Error={e} | time={time.time()} | crawling_id={state['data'][0].get('crawling_id')}")
        return {
            **state,
            'retry_count': state.get('retry_count', 0) + 1,
        }

def evaluate_post(state: State) -> State:
    """완성된 게시글이 저장 가능한 품질인지 검사한다."""
    try:
        logger.info(f"evaluate_post start | shop_id={state['data'][0].get('shop_id')}")
        result = evaluate_post_completion(state)
        logger.info(f"evaluate_post end | shop_id={state['data'][0].get('shop_id')} | is_pass={result.get('is_pass')} | reason={result.get('reason')}")
        return {
            **state,
            'is_pass': result.get('is_pass'),
            'reason': result.get('reason'),
        }

    except Exception as e:
        logger.error(f"Error={e} | time={time.time()} | crawling_id={state['data'][0].get('crawling_id')}")
        return state

def route_after_embedding(state: State) -> str:
    """유사 게시글이 발견되면 바로 재생성으로 보내 중복을 줄인다."""
    if state.get('similar_post'):
        if state.get('retry_count', 0) >= 2:
            return "end"
        return "regenerate_post"
    return "evaluate_post"


def route_after_evaluation(state: State) -> str:
    """평가 통과 또는 최대 재시도 도달 시 그래프를 종료한다."""
    if state.get('is_pass'):
        return "end"
    if state.get('retry_count', 0) >= 2:
        return "end"
    return "regenerate_post"


def build_graph():
    """게시글 생성부터 평가까지의 LangGraph 흐름을 구성한다."""
    graph = StateGraph(State)
    graph.add_node("make_post", make_post)
    graph.add_node("make_title", make_title)
    graph.add_node("embedding", embedding)
    graph.add_node("regenerate_post", regenerate_post)
    graph.add_node("evaluate_post", evaluate_post)
    graph.add_edge(START, "make_post")
    graph.add_edge("make_post", "make_title")
    graph.add_edge("make_title", "embedding")

    # 기존 게시글과 유사하면 평가 전에 먼저 재생성한다.
    graph.add_conditional_edges(
        "embedding",
        route_after_embedding,
        {
            "regenerate_post": "regenerate_post",
            "evaluate_post": "evaluate_post",
            "end": END,
        }
    )
    graph.add_edge("regenerate_post", "make_title")

    # 평가 실패 시 최대 retry_count까지 재생성하고, 다시 제목/유사도 검사를 거친다.
    graph.add_conditional_edges(
        "evaluate_post",
        route_after_evaluation,
        {
            "regenerate_post": "regenerate_post",
            "end": END,
        }
    )
    return graph.compile()


graph = build_graph()
