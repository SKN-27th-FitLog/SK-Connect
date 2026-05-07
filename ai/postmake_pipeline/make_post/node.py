from langgraph.graph import StateGraph, START, END
from langchain_huggingface import HuggingFaceEmbeddings
from typing import TypedDict
from common.logging_config import set_logging
from common.connection import Connection, PGVectorStore
from make_post.evaluation import evaluate_post_completion
from common.llm_factory import get_llm
from typing import Optional
from get_data.get_another import get_similar_post
from common.prompt import get_prompt, get_title_prompt, get_regenerate_prompt, get_regenerate_reason_prompt
from get_data.get_another import get_image
import time
import os
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


"""===================================================================="""

class State(TypedDict):
    keyword: list[str]
    data: list[dict]
    post: Optional[str]
    title: Optional[str]
    similar_post: Optional[list[str]]
    reason: Optional[str]


def make_post(state: State) -> State:
    try:
        llm = get_llm()
        image_list = get_image(state['data'])
        prompt = get_prompt(state['keyword'], image_list, state['data'][0].get('article_url'))
        response = llm.invoke(prompt)
        
        return {
            **state,
            'post': response.content if hasattr(response, "content") else str(response),
        }
    except Exception as e:
        logger.error(f"Error={e} | time={time.time()} | crawling_id={state['data'][0].get('crawling_id')}")
        return state

def make_title(state: State) -> State:
    try:
        llm = get_llm()
        prompt = get_title_prompt(state['post'])
        response = llm.invoke(prompt)
        return {
            **state,
            'title': response.content if hasattr(response, "content") else str(response),
        }
    except Exception as e:
        logger.error(f"Error={e} | time={time.time()} | crawling_id={state['data'][0].get('crawling_id')}")
        return state

def embedding(state: State) -> State:
    try:
        vectorstore = get_vectorstore()
        results = vectorstore.similarity_search(state['post'], k=5)
        if results:
            state['similar_post'] = get_similar_post(results)
        return state
    except Exception as e:
        logger.error(f"Error={e} | time={time.time()} | crawling_id={state['data'][0].get('crawling_id')}")
        return state

def regenerate_post(state: State) -> State:
    try:
        llm = get_llm()
        if state['reason']:
            prompt = get_regenerate_reason_prompt(state['reason'])
        elif state['similar_post']:
            prompt = get_regenerate_prompt(state['similar_post'])
        else:
            return state
        response = llm.invoke(prompt)
        return {
            **state,
            'post': response.content if hasattr(response, "content") else str(response),
        }
    except Exception as e:
        logger.error(f"Error={e} | time={time.time()} | crawling_id={state['data'][0].get('crawling_id')}")
        return state

def evaluate_post(state: State) -> State:
    try:
        state['reason'] = evaluate_post_completion(state)
        return state

    except Exception as e:
        logger.error(f"Error={e} | time={time.time()} | crawling_id={state['data'][0].get('crawling_id')}")
        return state

def route_after_embedding(state: State) -> str:
    if state.get('similar_post'):
        return "regenerate_post"
    return "evaluate_post"


def graph():

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
    graph.add_edge("evaluate_post", END)
    return graph.compile()
