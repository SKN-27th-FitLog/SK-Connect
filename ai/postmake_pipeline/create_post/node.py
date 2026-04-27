from langchain_huggingface import HuggingFaceEmbeddings
from typing import TypedDict, List
from common.logging_config import set_logging
from common.connection import Connection, PGVectorStore
from create_post.evaluation import evaluate_post_completion
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
    data: dict #전처리 된 데이터
    post: str #게시글 생성 결과
    prompt: str #프롬프트
    embedding: List[float] #data의 content를 임베딩 벡터로 변환
    is_unique: bool #embedding과 유사한 데이터 존재 여부
    similar_posts: List[dict] #embedding과 유사한 데이터



def graph():

    
    return graph.compile()
