# 로그 
import logging
logger = logging.getLogger(__name__)

import os # 단독실행 테스트 시 
from dotenv import load_dotenv

# 패키지
from neo4j import GraphDatabase
from langchain_core.documents import Document
from langchain_ollama import OllamaEmbeddings
from .n4j_query_templates import CypherQueryTemplates

# 모듈
from common.db.connection import Singleton


#####################################################################################
# 싱글톤 클래스 상속받아서 neo4j 연결 객체 생성
#####################################################################################
class Neo4j_Connection(metaclass=Singleton):
    '''Neo4j 데이터 베이스 연결 객체 생성 및 관련 메서드 내장 클래스 정의 '''

    def __init__(self, uri, user, password, embedding_model="qwen3-embedding:0.6b"):
        '''
        객체 생성 시 초기화 매서드
        드라이버 및 임베딩 모델 생성 시점에 초기화 하고 키값 설정도 변수 받아서 내장 
        ''' 
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        self.embedding_model = OllamaEmbeddings(model=embedding_model)
        logger.info(f"Neo4j 연결 성공: {uri}")
        logger.info(f"임베딩 모델: {embedding_model}")

    def close(self):
        '''
        해당 메소드 실행해서 리소스를 놓아주기 위함 
        '''
        self.driver.close()
        logger.info("Neo4j 드라이버 연결 해제 완료")

    def execute_query(self, query:str="", parameters:dict=None) -> list:
        '''
        session.run을 래핑해서 간단한 리스트 형태로 결과를 반환 시킴
        '''
        with self.driver.session() as session:
            result = session.run(query, parameters)
            return [record for record in result]

    def execute_query_templates(self, template:str="", parameters:dict=None) -> list:
        if template not in CypherQueryTemplates.__members__:
            raise Exception(f"Invalid template: {template}")

        # enum 기반 탬플릿을 통해 최종 cypher 쿼리 생성
        cypher_query = CypherQueryTemplates[template].bulid(**parameters)
        results = self.exxecute_query(cypher_query)

        documents = []
        for result in results:
            # 결과 레코드를 langchain document와 score 페어로 변환
            doc = Document(
                page_content=f"[뉴스제목] {result['title']}\n[뉴스내용] {result['content']}",
                metadata={
                    "publisher_name": result['publisher_name'],
                    "reporter_name": result['reporter_name'],
                    "published_date": result['published_date'],
                    "source": result['news_link'],
                }
            )
            documents.append(doc, result['score'])

        return documents







if __name__ == "__main__":

    # 단독 실행 시 기본 설정 
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(filename)s %(message)s", )
    load_dotenv()

    # 테스트 시작 
    logger.info("=== Neo4j 연결 테스트 ===")

    neo4j_connection = Neo4j_Connection(
        uri=os.getenv("NEO4J_URI"),
        user=os.getenv("NEO4J_USER"),
        password=os.getenv("NEO4J_PASSWORD"),
        embedding_model=os.getenv("NEO4J_EMBEDDING_MODEL")
    )