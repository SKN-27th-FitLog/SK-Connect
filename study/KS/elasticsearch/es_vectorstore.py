# 패키지
from langchain_ollama import OllamaEmbeddings
from elasticsearch import Elasticsearch
from connection import ElasticsearchVectorStore

# 모듈
from connection import ElasticsearchVectorStore


############################################### 
# Elasticsearch VectorStore 
###############################################
def create_elasticsearch_vectorstore():
    """ 벡터 스토어 생성 함수 """

    # embeddings
    embeddings = OllamaEmbeddings(model="qweb3-embedding:0.6b")

    # elasticsearch connection 
    es_client = Elasticsearch(
        ["http://localhost:9200"],  # 리스트 형태로, scheme 포함
        basic_auth=("elastic", "changeme123!"),  # 인증 정보 (보안 활성화 시 필수)
        verify_certs=False,
        ssl_show_warn=False,
        request_timeout=30,
        max_retries=3,
        retry_on_timeout=True,
        # 호환성 헤더 비활성화 (개발 환경용)
        headers={"accept": "application/json", "content-type": "application/json"}
    )

    # 인덱스 이름
    index_name = "rag_keywords"

    # vectorstore 생성
    vectorstore = ElasticsearchVectorStore(
        es_client=es_client,
        index_name=index_name,
        embeddings=embeddings,
        k=2
    )

    return vectorstore