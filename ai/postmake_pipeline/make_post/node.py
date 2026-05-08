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
    urls = []
    for image in image_list or []:
        if isinstance(image, dict):
            url = image.get('image_url') or image.get('url')
        else:
            url = str(image)
        if url:
            urls.append(str(url))
    return urls


def _ensure_media(post: str, image_list: Optional[list], url: Optional[str]) -> str:
    content = str(post or "").strip()
    image_urls = _extract_image_urls(image_list)
    if image_urls and not any(image_url in content for image_url in image_urls):
        content = f"{content}\n\n{image_urls[0]}"
    if url and str(url) not in content:
        content = f"{content}\n\n{url}"
    return content


"""===================================================================="""

class State(TypedDict):
    keyword: list[str]
    data: list[dict]
    post: Optional[str]
    title: Optional[str]
    similar_post: Optional[list[str]]
    reason: Optional[str]
    sample_data: Optional[dict]
    is_pass: Optional[bool]
    retry_count: int


def make_post(state: State) -> State:
    try:
        logger.info(f"make_post start | shop_id={state['data'][0].get('shop_id')}")
        llm = get_llm()
        image_list = get_image(state['data'])
        sample_data = random.choice(state['data']) if state['data'] else None
        url = sample_data.get('article_url') if sample_data else state['data'][0].get('article_url')
        prompt = Create_Prompt.get_prompt(state['keyword'], image_list, url, sample_data)
        response = llm.invoke(prompt)
        post = response.content if hasattr(response, "content") else str(response)
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
    try:
        logger.info(f"make_title start | shop_id={state['data'][0].get('shop_id')}")
        llm = get_llm()
        prompt = Create_Prompt.get_title_prompt(state['post'])
        response = llm.invoke(prompt)
        title = response.content if hasattr(response, "content") else str(response)
        logger.info(f"make_title end | shop_id={state['data'][0].get('shop_id')} | title_len={len(title)}")
        return {
            **state,
            'title': title,
        }
    except Exception as e:
        logger.error(f"Error={e} | time={time.time()} | crawling_id={state['data'][0].get('crawling_id')}")
        return state

def embedding(state: State) -> State:
    try:
        logger.info(f"embedding start | shop_id={state['data'][0].get('shop_id')}")
        vectorstore = get_vectorstore()
        results = vectorstore.similarity_search(state['post'], k=5)
        if results:
            state['similar_post'] = get_similar_post(results)
        logger.info(f"embedding end | shop_id={state['data'][0].get('shop_id')} | similar_count={len(state.get('similar_post') or [])}")
        return state
    except Exception as e:
        logger.error(f"Error={e} | time={time.time()} | crawling_id={state['data'][0].get('crawling_id')}")
        return state

def regenerate_post(state: State) -> State:
    try:
        retry_count = state.get('retry_count', 0)
        if retry_count >= 2:
            return state
        logger.info(f"regenerate_post start | shop_id={state['data'][0].get('shop_id')} | retry_count={retry_count}")
        llm = get_llm()
        image_list = get_image(state['data'])
        sample_data = state.get('sample_data') or (random.choice(state['data']) if state['data'] else None)
        url = sample_data.get('article_url') if sample_data else state['data'][0].get('article_url')
        if state['reason']:
            prompt = Create_Prompt.get_regenerate_reason_prompt(state['reason'], state['keyword'], image_list, url, sample_data)
        elif state['similar_post']:
            prompt = Create_Prompt.get_regenerate_prompt(state['similar_post'], state['keyword'], image_list, url, sample_data)
        else:
            return state
        response = llm.invoke(prompt)
        post = response.content if hasattr(response, "content") else str(response)
        post = _ensure_media(post, image_list, url)
        logger.info(f"regenerate_post end | shop_id={state['data'][0].get('shop_id')} | retry_count={retry_count + 1} | post_len={len(post)}")
        return {
            **state,
            'post': post,
            'sample_data': sample_data,
            'retry_count': retry_count + 1,
        }
    except Exception as e:
        logger.error(f"Error={e} | time={time.time()} | crawling_id={state['data'][0].get('crawling_id')}")
        return {
            **state,
            'retry_count': state.get('retry_count', 0) + 1,
        }

def evaluate_post(state: State) -> State:
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
    if state.get('similar_post'):
        return "regenerate_post"
    return "evaluate_post"


def route_after_evaluation(state: State) -> str:
    if state.get('is_pass'):
        return "end"
    if state.get('retry_count', 0) >= 2:
        return "end"
    return "regenerate_post"


def build_graph():

    graph = StateGraph(State)
    graph.add_node("make_post", make_post)
    graph.add_node("make_title", make_title)
    graph.add_node("embedding", embedding)
    graph.add_node("regenerate_post", regenerate_post)
    graph.add_node("evaluate_post", evaluate_post)
    graph.add_edge(START, "make_post")
    graph.add_edge("make_post", "make_title")
    graph.add_edge("make_title", "embedding")
    graph.add_conditional_edges(
        "embedding",
        route_after_embedding,
        {
            "regenerate_post": "regenerate_post",
            "evaluate_post": "evaluate_post",
        }
    )
    graph.add_edge("regenerate_post", "evaluate_post")
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
