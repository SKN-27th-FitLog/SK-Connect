# 환경변수 
from dotenv import load_dotenv
load_dotenv()

# 로그
import logging
logger = logging.getLogger(__name__)

# 패키지
import os
import streamlit as st
import pandas as pd
import ast

# GraphDatabase: Neo4j 데이터베이스와 통신하기 위한 드라이버 클래스
from neo4j import GraphDatabase
from graphdatascience import GraphDataScience
from qurry_neo4j import run_query



# ============================================
# 접속정보 생성 
# ============================================
def get_neo4j_config():
    '''
    환경변수에 설정된 키 값들을 가져와서 연결정보 생성 
    '''
    return {
        "URI": os.getenv("NEO4J_URI"),
        "USERNAME": os.getenv("NEO4J_USER"),
        "PASSWORD": os.getenv("NEO4J_PASSWORD")
    }


# ============================================
# 드라이버 객체 생성 
# ============================================

def get_neo4j_driver():
    '''
    연결정보를 가지고 드라이버 객체를 반환하는 함수 
    '''
    neo4j_config = get_neo4j_config()

    # ============================================
    # Neo4j 드라이버 생성
    # ============================================
    # driver: Neo4j 데이터베이스와의 연결을 관리하는 드라이버 객체
    # GraphDatabase.driver(): URI와 인증 정보를 사용하여 드라이버 생성
    driver = GraphDatabase.driver(
        uri=neo4j_config["URI"], 
        auth=(neo4j_config["USERNAME"], neo4j_config["PASSWORD"])
    )

    # ============================================
    # GDS 객체 생성
    # ============================================
    # GraphDataScience: GDS 라이브러리의 메인 클래스
    # driver: Neo4j 드라이버 객체를 전달
    gds = GraphDataScience(neo4j_config["URI"], auth=(neo4j_config["USERNAME"], neo4j_config["PASSWORD"]))

    return driver, gds


def test_neo4j_driver(driver=None):
    '''
    연결 테스트를 진행하기 위한 간이 함수 
    '''
    # ============================================
    # 연결 테스트
    # ============================================
    # Neo4j 연결이 정상적으로 작동하는지 확인합니다.
    try:
        # 간단한 테스트 쿼리 실행
        # "RETURN 1 as test": 숫자 1을 반환하는 간단한 쿼리
        result = run_query("RETURN 1 as test", driver=driver)
        logger.info("Neo4j 연결 성공!")
    except Exception as e:
        # 연결 실패 시 에러 메시지 출력
        logger.info(f"Neo4j 연결 실패: {e}")




if __name__ == "__main__":

    logging.basicConfig(level=logging.INFO)

    driver, gds = get_neo4j_driver()
    test_neo4j_driver(driver=driver)
