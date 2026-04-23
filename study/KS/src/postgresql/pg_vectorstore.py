import os
os.environ["PYTHONPATH"] = "C:\\dev\\project\\SK-Connect\\study\\KS\\src"
os.system("python C:\\dev\\project\\SK-Connect\\study\\KS\\src\\postgresql\\pg_vectorstore.py")

# 패키지 
import logging
from langchain_ollama import OllamaEmbeddings

# 모듈
from connection import CustomPGVector
from common.loader import load_text_data

def create_custom_pgvector():
    """ PostgreSQL VectorStore 생성 함수 """
    # 임배딩 모델 생성 
    embeddings = OllamaEmbeddings(model="qweb3-embedding:0.6b")

    # PostgreSQL VectorStore 생성 
    vectorstore = CustomPGVector(
        conn_str="postgresql://admin:admin123@localhost:5433/langchain_db",
        embedding_fn=embeddings,
        table='documents'
    )

    return vectorstore


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)


    # PostgreSQL VectorStore 생성 
    vectorstore = create_custom_pgvector()
    logger.info(f"PostgreSQL VectorStore 생성 완료: {vectorstore}")

    # 데이터 로드 
    documents = load_text_data("data/*.txt")

    # vectorstore에 데이터 추가 
    vectorstore.add_texts(documents)
    logger.info(f"데이터 추가 완료: {len(documents)}개")