from langchain_ollama import ChatOllama
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.prompts import ChatPromptTemplate
from typing import TypedDict, List
from langgraph.graph import StateGraph, START, END
from src.logging_config import set_logging
from src.to_post import get_vectorstore, get_connection
logger = set_logging()

import os

#llm 모델설정
#embedding 모델설정
#similarity_search
#invoke
def get_llm():
    return ChatOllama(
        model="gemma4:e4b",
        temperature=0.1,
        num_predict=500,
        keep_alive="20m",
    )

#CRAG
class State(TypedDict):
    data: dict #전처리 된 데이터
    post: str #게시글 생성 결과
    prompt: str #프롬프트
    embedding: List[float] #data의 content를 임베딩 벡터로 변환
    is_unique: bool #embedding과 유사한 데이터 존재 여부
    similar_posts: List[dict] #embedding과 유사한 데이터
    status: str #CRAG 판정 결과
    failed_crawling_id: int | None #실패한 crawling_id
    retry_count: int #재생성 횟수
    max_retry: int #최대 재생성 횟수

def get_data_node(state: State):
    """전처리 된 데이터를 받아와 data 키에 저장"""
    return {
        **state,
        "data": state["data"]
    }


def embedding_node(state: State):
    """크롤링 데이터를 받아와 embedding 벡터를 생성"""
    state["embedding"] = HuggingFaceEmbeddings(
        model_name = 'google/embeddinggemma-300m',
        hf_token = os.getenv("HF_TOKEN"),
    ).embed_query(state["data"]["content"])

    return {
        **state,
        "embedding": state["embedding"]
    }

def validate_post_similarity(data: dict, similar_posts: List[dict]) -> bool:
    """게시글 중복 검사(LLM)"""
    if not similar_posts:
        return True

    llm = get_llm()
    prompt = ChatPromptTemplate.from_template(
        """
        # [SYSTEM ROLE]
        당신은 게시글 중복 검사를 담당하는 전문가입니다.
        아래 신규 게시글과 기존 유사 게시글 목록을 보고, 중복이면 failed, 아니면 passed만 출력하세요.

        # [NEW POST]
        {data}

        # [SIMILAR POSTS]
        {similar_posts}
        """
    )
    response = llm.invoke(prompt.format(data=str(data), similar_posts=str(similar_posts)))
    result = response.content if hasattr(response, "content") else str(response)
    return "passed" in result.lower()

def check_existing_post_by_map_id(map_id: str | None) -> bool:
    """post 테이블에서 map_id 기준 중복 체크"""
    if map_id is None:
        return False

    try:
        query = """
        SELECT 1
        FROM posts
        WHERE map_id = %s
        LIMIT 1
        """
        cursor = get_connection().cursor()
        cursor.execute(query, (map_id,))
        return cursor.fetchone() is not None
    except Exception as e:
        logger.error(f"Error={e}")
        return False

def similarity_search_node(state: State):
    """임베딩한 데이터와 유사한 데이터를 post_vector 테이블에서 검색, 만약
    유사한 데이터가 있다면 row 가져와서 self.similar_posts에 추가"""
    # map_id 기준으로 DB 중복 검사 1회
    if check_existing_post_by_map_id(state["data"].get("map_id")):
        return {
            **state,
            "is_unique": False,
            "similar_posts": [{"source": "posts_by_map_id"}]
        }

    vectorstore = get_vectorstore()
    similar_docs = vectorstore.similarity_search_by_vector(state["embedding"], k=20)
    similar_posts = [{"page_content": d.page_content, "metadata": d.metadata} for d in similar_docs]

    if similar_posts is None:
        return {
            **state,
            "is_unique": True,
            "similar_posts": []
        }

    elif similar_posts is not None:
        is_unique = validate_post_similarity(state["data"], similar_posts)
        return {
            **state,
            "is_unique": is_unique,
            "similar_posts": similar_posts
        }

def regenerate_node(state: State):
    """유사 게시글이 있는 경우 게시글 재생성"""
    llm = get_llm()
    response = llm.invoke(state["prompt"])
    post = response.content if hasattr(response, "content") else str(response)

    data = state["data"].copy()
    data["content"] = post

    return {
        **state,
        "post": post,
        "data": data
    }

def crag_node(state: State):
    """유사도 검색 결과 기준 CRAG 판정"""
    if state["is_unique"]:
        return {
            **state,
            "status": "passed",
            "failed_crawling_id": None
        }

    if state["retry_count"] < state["max_retry"]:
        return {
            **state,
            "status": "retry",
            "retry_count": state["retry_count"] + 1
        }

    return {
        **state,
        "status": "failed",
        "failed_crawling_id": state["data"]["crawling_id"]
    }

def route_crag(state: State):
    """CRAG 분기"""
    if state["status"] == "retry":
        return "retry"
    return "done"

def graph():
    graph = StateGraph(State)
    graph.add_node("get_data", get_data_node)
    graph.add_node("embedding", embedding_node)
    graph.add_node("similarity_search", similarity_search_node)
    graph.add_node("regenerate", regenerate_node)
    graph.add_node("crag", crag_node)

    graph.add_edge(START, "get_data")
    graph.add_edge("get_data", "embedding")
    graph.add_edge("embedding", "similarity_search")
    graph.add_edge("similarity_search", "crag")
    graph.add_conditional_edges(
        "crag",
        route_crag,
        {
            "retry": "regenerate",
            "done": END
        }
    )
    graph.add_edge("regenerate", "embedding")
    
    return graph.compile()
