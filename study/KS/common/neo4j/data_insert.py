# 로그 
import logging
logger = logging.getLogger(__name__)

# 패키지 
import os
from dotenv import load_dotenv
import pandas as pd
from pathlib import Path
from neo4j import GraphDatabase
from graphdatascience import GraphDataScience

# 모듈
from connection import Neo4j_Connection


###########################################################
# 데이터가 있는 파일 path 정의 
###########################################################
_DATA_DIR = Path(__file__).resolve().parent / "data"


###########################################################
# 지정 테이블 쿼리  
###########################################################

# 장비 아이템 쿼리 및 데이터 반환 
def import_equipment(row):
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

    rows = {
        "id": str(row["RowName"]),
        "name": row["Name"],
        "type": row["Type"],
        "detail_type": row["DetailType"],
        "grade": row["Grade"],
    }

    return query, rows




if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    load_dotenv()


    ############################################################
    # 데이터 가져오기 
    ############################################################
    df = pd.read_csv(_DATA_DIR / "Item_Equipment_cleaned.csv")
    logger.info('=== 로드된 데이터 확인 ===')
    logger.info(df.columns.tolist())
    logger.info(df.shape)


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
    # Neo4j 에 지정 데이터 추가 쿼리 실행 
    ############################################################
    for _, row in df.iterrows():
        query, rows = import_equipment(row)
        result = driver.execute_query(query, rows)
        logger.info(result)

    logger.info("Neo4j 적재 완료!")

