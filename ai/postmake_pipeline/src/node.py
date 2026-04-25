from langchain_ollama import ChatOllama
from langchain_huggingface import HuggingFaceEmbeddings
from typing import TypedDict, List
from langgraph.graph import StateGraph, START, END
from src.from_crawling import cursor_excute
import os

def get_llm():
    return ChatOllama(
        model="gemma4:e4b",
        temperature=0.1,
        num_predict=500,
        keep_alive="20m",
    )

class State(TypedDict):
    data: dict
    post: str
    prompt: str
    embedding: List[float]
    is_unique: bool
    similar_posts: list[dict]

def embedding_node(state: State):
    """크롤링 데이터를 받아와 embedding 벡터를 생성"""
    state["embedding"] = HuggingFaceEmbeddings(
        model_name = 'google/embeddinggemma-300m',
        token = os.getenv("HF_TOKEN"),
    ).embed_query(state["data"]["content"])

    return {
        **state,
        "embedding": state["embedding"]
    }

def similarity_search_node(state: State):
    """임베딩한 데이터와 유사한 데이터를 post_vector 테이블에서 검색"""
    query = """
    SELECT * FROM post_vector
    WHERE embedding = %s
    ORDER BY embedding <-> %s
    LIMIT 20
    """
    return{
        **state,
        "similar_posts": cursor_excute(query, (state["embedding"], state["embedding"]))
    }




def graph():
    graph = StateGraph(State)
    graph.add_node("embedding", embedding_node)
    graph.add_node("similarity_search", similarity_search_node)
    graph.add_edge(START, "embedding")
    graph.add_edge("embedding", "similarity_search")
    graph.add_edge("similarity_search", "mk_post")
    graph.add_edge("mk_post", END)
    return graph.compile()
