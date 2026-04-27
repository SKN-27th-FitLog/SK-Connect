from langchain_huggingface import HuggingFaceEmbeddings
from typing import TypedDict, List
from langgraph.graph import StateGraph, START, END
from src.logging_config import set_logging
from src.to_post import get_vectorstore, get_connection
from src.validator import validate_post_completion
from src.llm_factory import get_llm
logger = set_logging()

import os

_EMBEDDINGS_SINGLETON = None
COSINE_DISTANCE_THRESHOLD = 0.08  # cosine similarity 0.92 이상이면 중복으로 판단
MIN_GENERATED_CHARS = 200

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


def _fail_or_retry(state: State):
    """공통 재시도/실패 분기"""
    current_retry = state.get("retry_count", 0)
    max_retry = state.get("max_retry", 2)
    if current_retry < max_retry:
        return {
            **state,
            "status": "retry",
            "retry_count": current_retry + 1,
        }
    return {
        **state,
        "status": "failed",
        "failed_crawling_id": state["data"]["crawling_id"],
    }


def _build_regenerate_prompt(state: State) -> str:
    """유사 검색 결과를 반영해 재생성용 프롬프트를 보강"""
    similar_posts = state.get("similar_posts") or []
    if not similar_posts:
        return state["prompt"]

    samples: list[str] = []
    for idx, post in enumerate(similar_posts[:3], start=1):
        content = str(post.get("page_content") or "").strip() if isinstance(post, dict) else ""
        if content:
            samples.append(f"[유사글 {idx}] {content[:300]}")

    if not samples:
        return state["prompt"]

    return (
        f"{state['prompt']}\n\n"
        "[추가 지시]\n"
        "아래 유사글과 문장/전개가 겹치지 않게 완전히 새롭게 작성하세요.\n"
        "- 문장 복붙/짜깁기 금지\n"
        "- 핵심 사실은 유지하되 어휘/구성은 새롭게\n\n"
        "[유사글 샘플]\n"
        f"{chr(10).join(samples)}"
    )

def generate_post_node(state: State):
    """프롬프트 기반 게시글 1회 생성 후 data.content 교체"""
    llm = get_llm()
    response = llm.invoke(state["prompt"])
    post = response.content if hasattr(response, "content") else str(response)
    post = (post or "").strip()
    if len(post) < MIN_GENERATED_CHARS:
        logger.warning("Generated post too short/empty (single attempt)")
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
    embedding = embeddings.embed_query(state["data"]["content"])

    return {
        **state,
        "embedding": embedding
    }

def check_existing_post(data: dict) -> tuple[bool, list[dict]]:
    """post 테이블에서 title + map_id 기준 기존 게시글 조회"""
    title = str(data.get("title") or "").strip()
    map_id = data.get("map_id")
    if not title or map_id is None:
        return False, []

    try:
        connection = get_connection()
        query = """
        SELECT post_id, title, content, modify_at
        FROM posts
        WHERE LOWER(TRIM(title)) = LOWER(TRIM(%s))
          AND map_id = %s
          AND post_cd = %s
        ORDER BY modify_at DESC, post_id DESC
        LIMIT 3
        """
        with connection.cursor() as cursor:
            cursor.execute(query, (title, map_id, "PT01"))
            rows = cursor.fetchall()
            existing_posts = [
                {
                    "post_id": row[0],
                    "title": row[1],
                    "page_content": row[2],
                    "modify_at": row[3],
                    "source": "posts_by_title_map_id",
                }
                for row in rows
            ]
        # SELECT 이후 트랜잭션을 즉시 정리해 open transaction 상태 종료
        connection.rollback()
        return len(existing_posts) > 0, existing_posts
    except Exception as e:
        logger.error(f"Error={e} | title={title} | map_id={map_id}")
        try:
            get_connection().rollback()
        except Exception:
            pass
        return False, []

def similarity_search_node(state: State):
    """임베딩한 데이터와 유사한 데이터를 post_vector 테이블에서 검색, 만약
    유사한 데이터가 있다면 row 가져와서 self.similar_posts에 추가"""
    # map_id 기준으로 DB 중복 검사 1회
    exists, existing_posts = check_existing_post(state["data"])
    if exists:
        return {
            **state,
            "is_unique": False,
            "similar_posts": existing_posts
        }

    vectorstore = get_vectorstore(state["data"].get("category_cd"))
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


def route_similarity(state: State):
    """유사도 분기: 없으면 생성, 있으면 재생성"""
    return "generate" if state.get("is_unique", True) else "regenerate"


def regenerate_node(state: State):
    """유사글 존재 시 재생성"""
    regenerate_state = {
        **state,
        "prompt": _build_regenerate_prompt(state),
    }
    return generate_post_node(regenerate_state)

def crag_node(state: State):
    """생성 결과 완성도 기준 CRAG 판정"""
    is_valid_post = validate_post_completion(state)

    if not is_valid_post:
        return _fail_or_retry(state)

    return {
        **state,
        "status": "passed",
        "failed_crawling_id": None
    }

def route_crag(state: State):
    """CRAG 분기"""
    return "retry" if state["status"] == "retry" else "done"

def graph():
    graph = StateGraph(State)
    graph.add_node("embedding", embedding_node)
    graph.add_node("similarity_search", similarity_search_node)
    graph.add_node("generate_post", generate_post_node)
    graph.add_node("regenerate", regenerate_node)
    graph.add_node("crag", crag_node)

    graph.add_edge(START, "embedding")
    graph.add_edge("embedding", "similarity_search")
    graph.add_conditional_edges(
        "similarity_search",
        route_similarity,
        {
            "generate": "generate_post",
            "regenerate": "regenerate"
        }
    )
    graph.add_edge("generate_post", "crag")
    graph.add_edge("regenerate", "crag")
    graph.add_conditional_edges(
        "crag",
        route_crag,
        {
            "retry": "regenerate",
            "done": END
        }
    )
    
    return graph.compile()
