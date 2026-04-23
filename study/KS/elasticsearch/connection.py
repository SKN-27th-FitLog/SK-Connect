# 패키지 
from typing import List, Tuple
from langchain_core.vectorstores.base import VectorStore
from langchain_core.documents import Document

# 모듈 
from src.utils.singleton import Singleton


#######################################################
# Elasticsearch VectorStore 클래스 (singleton)
#######################################################
class ElasticsearchVectorStore(VectorStore, metaclass=Singleton):
    """ ElasticSearch 연결 클래스 , 싱글톤 패턴 적용"""

    def __init__(self, es_client, index_name, embeddings, k=2):
        self.es_client      = es_client
        self.index_name     = index_name
        self._embeddings    = embeddings
        self.k              = k

    @classmethod
    def from_texts(cls, **kwargs):
        """VectorStore 상속을 받기 위한 필수 함수 선언"""
        pass

    ###############################################################
    # 유사도 검색 (sinilarity search)
    ###############################################################
    def __search_similarity(self, query:str, k:int):
        """ knn 서치로 유사도 검색 """
        # 쿼리 덱스트를 임배딩으로 변환 
        query_embedding = self._embeddings.embed_query(query)
        
        # KNN 유사도 서치 (문서와 쿼리의 벡터 유사도 비교)
        search_query = {
            "knn": {
                "field": "embedding",
                "query_vector": query_embedding,
                "k": k,
                "num_candidates": 100, # 추천 후보 문서 수 
            },
            "_source": ["text", "metadata"] # 반환할 필드 
        }

        # 검색 실행 
        return self.es_client.search(index=self.index_name, body=search_query)

    def similarity_search(self, query:str, k:int=4 ) -> List[Document]:
        """ 임배딩 백터 유사도 검색 함수 """
        # 검색 실행 
        response = self.__search_similarity(query, k)
        # 결과 파싱
        documents=[]
        for hit in response['hits']['hits']:
            doc=Document(
                page_content=hit['_source']['text'], 
                metadata=hit['_source'].get('metadata', {})
            )
            # 결과를 순회하면서 문서 리스트에 문서들을 추가 
            documents.append(doc)
        return documents

    def similarity_search_with_score(self, query:str, k:int=4 ) -> List[Tuple[Document, float]]:
        """ 임배딩 백터 유사도 검색 함수 (점수 반환) """
        # 검색 실행 
        response = self.__search_similarity(query, k)
        # 결과 파싱
        documents=[]
        for hit in response['hits']['hits']:
            doc=Document(
                page_content=hit['_source']['text'], 
                metadata=hit['_source'].get('metadata', {})
            )
            # 문서와 해당 문서의 유사도 점수를 튜플로 묶어서 리스트에 추가 
            documents.append( (doc, hit['_score']) )
        return documents


    ###############################################################
    # 복합 검색 (hybrid search = KNN similarity search + keyword search)
    ###############################################################
    def __search_hybrid(self, query:str, k:int):
        """ 복합 검색 (hybrid search = KNN similarity search + keyword search) """
        # 쿼리 덱스트를 임배딩으로 변환 
        query_embedding = self._embeddings.embed_query(query)
        
        # 하이브리드 검색 쿼리 
        search_query = {
            # BM25 키워드 검색
            "query":{"bool":{"should":[{"match":{"text":{"query":query, "boost":1.0 }}}]}},
            # KNN 유사도 검색
            "knn": {
                "field": "embedding",
                "query_vector": query_embedding,
                "k": k,
                "num_candidates": 100,
                "boost": 2.0  # 벡터 검색 가중치 (벡터에 더 높은 가중치)
            },
            "size":k,
            "_source": ["text", "metadata"] # 반환할 필드 
        }
        # 검색 실행
        return self.es_client.search(index=self.index_name, body=search_query)

    def hybrid_search(self, query:str, k:int=4 ) -> List[Document]:
        """ 복합 검색 (hybrid search = KNN similarity search + BM25 keyword search) """
        # 검색 실행 
        response = self.__search_hybrid(query, k)
        # 결과 파싱 / 점수랑 매핑 
        documents=[]
        for hit in response['hits']['hits']:
            doc=Document(
                page_content=hit['_source']['text'],
                metadata=hit['_source'].get('metadata', {})
            )
            documents.append((doc, hit['_score']))

        return documents