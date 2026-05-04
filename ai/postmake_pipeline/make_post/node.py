from langgraph.graph import StateGraph, START, END
from langchain_huggingface import HuggingFaceEmbeddings
from typing import TypedDict, List
from common.logging_config import set_logging
from common.connection import Connection, PGVectorStore
from make_post.evaluation import evaluate_post_completion
from common.llm_factory import get_llm
from typing import Optional
from get_data.get_similar_post import get_similar_post
from common.prompt import get_prompt, get_title_prompt
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
    data: dict
    post: Optional[str]
    title: Optional[str]
    similar_post: Optional[list[dict]]



def make_post(state: State) -> State:
    try:
        llm = get_llm()
        prompt = get_prompt(state['keyword'])
        response = llm.invoke(prompt)
        
        return {
            **state,
            'post': response,
        }
    except Exception as e:
        logger.error(f"Error={e} | time={time.time() | state['data']['crawling_id']}")
        return state

def embedding(state: State) -> bool:
    try:
        embeddings = get_embeddings()
        vectorstore = get_vectorstore()
        embedding = embeddings.embed_documents([state['post']])
        results = vectorstore.similarity_search(embedding, k=5)
        if results:
            state['similar_post'] = get_similar_post(results)
        elif not results:
            return False
    except Exception as e:
        logger.error(f"Error={e} | time={time.time() | state['data']['crawling_id']}")

def update_prompt(state: State) -> State:
    pass

def regenerate_post(state: State) -> State:
    try:
        llm = get_llm()
        prompt = get_regenerate_prompt(state['similar_post'])
        response = llm.invoke(prompt)
        return {
            **state,
            'post': response,
        }
    except Exception as e:
        logger.error(f"Error={e} | time={time.time() | state['data']['crawling_id']}")
        return state

def evaluate_post(state: State) -> bool:
    try:
        reason = evaluate_post_completion(state['post'])

    except Exception as e:
        logger.error(f"Error={e} | time={time.time() | state['data']['crawling_id']}")
        return False


def graph():

    graph = StateGraph(State)
    return graph.compile()
