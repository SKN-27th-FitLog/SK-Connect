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

# 모듈 
from connenct_neo4j import get_neo4j_driver


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
    logger.info("=== 기존 데이터 삭제 완료! ===")






if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(filename)s %(message)s", )

    driver, gds = get_neo4j_driver()
    clear_database(driver)
