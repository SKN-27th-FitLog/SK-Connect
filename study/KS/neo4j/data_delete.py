# 로그 
import logging
logger = logging.getLogger(__name__)

# 패키지 
import os
from dotenv import load_dotenv
import pandas as pd
from neo4j import GraphDatabase
from graphdatascience import GraphDataScience

# 모듈
from connection import Neo4j_Connection




if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    load_dotenv()

    ############################################################
    # Neo4j 드라이버 생성
    ############################################################
    driver = Neo4j_Connection(
        uri=os.getenv("NEO4J_URI"),
        user=os.getenv("NEO4J_USER"),
        password=os.getenv("NEO4J_PASSWORD"),
        embedding_model=os.getenv("NEO4J_EMBEDDING_MODEL")
    )

    ############################################################
    # Neo4j 메서드로 내장된 전체 데이터 삭제 쿼리 실행 
    ############################################################
    driver.clear_database()

    logger.info("Neo4j 전체 데이터 삭제 완료!")
