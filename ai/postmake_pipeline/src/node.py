from langchain_ollama import ChatOllama
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.prompts import ChatPromptTemplate
from typing import TypedDict, List
from langgraph.graph import StateGraph, START, END
from src.logging_config import set_logging
from src.to_post import get_vectorstore, get_connection
logger = set_logging()

import os
import time

_EMBEDDINGS_SINGLETON = None
COSINE_DISTANCE_THRESHOLD = 0.08  # cosine similarity 0.92 이상이면 중복으로 판단
MIN_GENERATED_CHARS = 20
MAX_GENERATION_RETRY = 2

#llm 모델설정
#embedding 모델설정
#similarity_search
#invoke
def get_llm():
    return ChatOllama(
        model="gemma4:e4b",
        temperature=0.2,
        num_predict=256,
        keep_alive="20m",
    )


def get_embeddings():
    """임베딩 모델 싱글톤 반환"""
    global _EMBEDDINGS_SINGLETON
    if _EMBEDDINGS_SINGLETON is None:
        model_kwargs = {}
        hf_token = os.getenv("HF_TOKEN")
        if hf_token:
            model_kwargs["token"] = hf_token

        _EMBEDDINGS_SINGLETON = HuggingFaceEmbeddings(
            model_name='sentence-transformers/all-mpnet-base-v2',
            model_kwargs=model_kwargs,
        )
    return _EMBEDDINGS_SINGLETON


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

def generate_post_node(state: State):
    """프롬프트 기반 게시글 1회 생성 후 data.content 교체"""
    llm = get_llm()
    current_prompt = state["prompt"]
    post = ""
    original_content = (state["data"].get("content") or "").strip()
    for attempt in range(MAX_GENERATION_RETRY):
        response = llm.invoke(current_prompt)
        post = response.content if hasattr(response, "content") else str(response)
        post = (post or "").strip()
        if len(post) >= MIN_GENERATED_CHARS:
            break
        current_prompt = (
            f"{state['prompt']}\n\n"
            "[추가 지시]\n"
            "- 응답은 반드시 비어있지 않은 한국어 본문으로 작성하세요.\n"
            f"- 최소 {MIN_GENERATED_CHARS}자 이상 작성하세요.\n"
            "- 제목/머리말/불릿 없이 본문만 출력하세요.\n"
        )
        logger.warning(f"Generated post too short/empty (attempt={attempt + 1})")
        time.sleep(0.5)
    if len(post) < MIN_GENERATED_CHARS:
        # 생성 실패 시 파이프라인 중단 대신 원문으로 fallback
        if len(original_content) > 0:
            logger.warning("LLM generation failed repeatedly, fallback to original content")
            post = original_content
        else:
            logger.warning("LLM generation failed and no original content, mark as failed")
            return {
                **state,
                "status": "failed",
                "failed_crawling_id": state["data"].get("crawling_id")
            }

    data = state["data"].copy()
    data["content"] = post

    return {
        **state,
        "post": post,
        "data": data
    }


def embedding_node(state: State):
    """크롤링 데이터를 받아와 embedding 벡터를 생성"""
    embeddings = get_embeddings()
    state["embedding"] = embeddings.embed_query(state["data"]["content"])

    return {
        **state,
        "embedding": state["embedding"]
    }

def check_existing_post(data: dict) -> bool:
    """post 테이블에서 title + map_id 기준 중복 체크"""
    title = data.get("title")
    map_id = data.get("map_id")
    if title is None:
        return False

    try:
        query = """
        SELECT 1
        FROM posts
        WHERE title = %s
        AND (
            map_id = %s
            OR (map_id IS NULL AND %s IS NULL)
        )
        LIMIT 1
        """
        cursor = get_connection().cursor()
        cursor.execute(query, (title, map_id, map_id))
        return cursor.fetchone() is not None
    except Exception as e:
        logger.error(f"Error={e}")
        return False

def similarity_search_node(state: State):
    """임베딩한 데이터와 유사한 데이터를 post_vector 테이블에서 검색, 만약
    유사한 데이터가 있다면 row 가져와서 self.similar_posts에 추가"""
    # map_id 기준으로 DB 중복 검사 1회
    if check_existing_post(state["data"]):
        return {
            **state,
            "is_unique": False,
            "similar_posts": [{"source": "posts_by_title_map_id"}]
        }

    vectorstore = get_vectorstore()
    try:
        similar_with_scores = vectorstore.similarity_search_with_score_by_vector(state["embedding"], k=20)
    except ValueError as e:
        # 초기 실행 시 컬렉션이 아직 없으면 중복 문서가 없는 상태로 간주
        if "Collection not found" in str(e):
            return {
                **state,
                "is_unique": True,
                "similar_posts": []
            }
        raise
    similar_posts = [
        {
            "page_content": doc.page_content,
            "metadata": doc.metadata,
            "score": score,
        }
        for doc, score in similar_with_scores
    ]

    # PGVector cosine distance 기준: 작을수록 유사
    is_duplicate_by_score = any(
        (p.get("score") is not None) and (p["score"] <= COSINE_DISTANCE_THRESHOLD)
        for p in similar_posts
    )
    is_unique = not is_duplicate_by_score

    return {
        **state,
        "is_unique": is_unique,
        "similar_posts": similar_posts
    }

def regenerate_node(state: State):
    """유사 게시글이 있는 경우 게시글 재생성"""
    llm = get_llm()
    current_prompt = state["prompt"]
    post = ""
    original_content = (state["data"].get("content") or "").strip()
    for attempt in range(MAX_GENERATION_RETRY):
        response = llm.invoke(current_prompt)
        post = response.content if hasattr(response, "content") else str(response)
        post = (post or "").strip()
        if len(post) >= MIN_GENERATED_CHARS:
            break
        current_prompt = (
            f"{state['prompt']}\n\n"
            "[추가 지시]\n"
            "- 응답은 반드시 비어있지 않은 한국어 본문으로 작성하세요.\n"
            f"- 최소 {MIN_GENERATED_CHARS}자 이상 작성하세요.\n"
            "- 제목/머리말/불릿 없이 본문만 출력하세요.\n"
        )
        logger.warning(f"Regenerated post too short/empty (attempt={attempt + 1})")
        time.sleep(0.5)
    if len(post) < MIN_GENERATED_CHARS:
        if len(original_content) > 0:
            logger.warning("LLM regeneration failed repeatedly, fallback to original content")
            post = original_content
        else:
            logger.warning("LLM regeneration failed and no original content, keep existing")
            post = state.get("post", "")

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

    # 비유니크 데이터는 즉시 실패 처리 (재생성 루프 제거)
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
    graph.add_node("generate_post", generate_post_node)
    graph.add_node("embedding", embedding_node)
    graph.add_node("similarity_search", similarity_search_node)
    graph.add_node("regenerate", regenerate_node)
    graph.add_node("crag", crag_node)

    graph.add_edge(START, "get_data")
    graph.add_edge("get_data", "generate_post")
    graph.add_edge("generate_post", "embedding")
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
