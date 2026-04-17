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

# 모듈
from common.db.connenct_neo4j import get_neo4j_driver



# ============================================
# Cypher 쿼리 실행 헬퍼 함수
# ============================================
def run_query(query, driver=None, parameters=None):
    """
    Cypher 쿼리를 실행하는 헬퍼 함수
    
    Args:
        query (str): 실행할 Cypher 쿼리 문자열
        parameters (dict, optional): 쿼리에 전달할 파라미터 딕셔너리
    
    Returns:
        list: 쿼리 결과 레코드들의 리스트
    
    사용 예시:
        result = run_query("MATCH (p:Person) RETURN p.name")
    """

    # driver.session(): 데이터베이스 세션 생성
    # 세션은 쿼리를 실행하는 컨텍스트를 제공합니다.
    with driver.session() as session:
        # session.run(): Cypher 쿼리를 실행
        # parameters or {}: 파라미터가 없으면 빈 딕셔너리 사용
        result = session.run(query, parameters or {})
        
        # 결과를 리스트로 변환하여 반환
        # record: 쿼리 결과의 각 행을 나타내는 객체
        return [record for record in result]


# ============================================
# 기존 데이터 삭제
# ============================================
# 주의: 모든 데이터가 삭제됩니다!
def clear_database(driver=None):
    """Neo4j의 모든 노드와 관계를 삭제"""
    with driver.session() as session:
        # MATCH (n): 모든 노드 선택
        # DETACH DELETE n: 노드와 연결된 모든 관계를 먼저 삭제한 후 노드 삭제
        # (DETACH 없이 DELETE하면 관계가 있는 노드는 삭제 불가)
        session.run("MATCH (n) DETACH DELETE n")
    logger.info("기존 데이터 삭제 완료!")




###########################################################
# 지정 테이블 쿼리  
###########################################################

# 장비 아이템 데이터 임포트 
def import_equipment(tx, row):
    query = """
    MERGE (e:Equipment {id: $id})
    SET e.name = $name

    MERGE (t:ItemType {name: $type})
    MERGE (dt:DetailType {name: $detail_type})
    MERGE (g:Grade {name: $grade})
    
    MERGE (e)-[:HAS_TYPE]->(t)
    MERGE (e)-[:HAS_DETAIL_TYPE]->(dt)
    MERGE (e)-[:HAS_GRADE]->(g)
    """
    tx.run(query, {
        "id": str(row["RowName"]),
        "name": row["Name"],
        "type": row["Type"],
        "detail_type": row["DetailType"],
        "grade": row["Grade"],
    })
