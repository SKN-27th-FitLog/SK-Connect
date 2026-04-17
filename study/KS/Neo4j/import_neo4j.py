# 로그 
import logging
logger = logging.getLogger(__name__)

# 패키지 
import os
import pandas as pd
from neo4j import GraphDatabase
from graphdatascience import GraphDataScience

# 모듈
from Neo4j.connenct_neo4j import get_neo4j_driver
from Neo4j.qurry_neo4j import import_equipment


###########################################################
# 데이터 적제 함수 
###########################################################
def main(df:pd.DataFrame):
    

    # ============================================
    # Neo4j 드라이버 생성
    # ============================================
    # driver: Neo4j 데이터베이스와의 연결을 관리하는 드라이버 객체
    # GraphDatabase.driver(): URI와 인증 정보를 사용하여 드라이버 생성
    driver, gds = get_neo4j_driver()


    with driver.session() as session:
        for _, row in df.iterrows():
            session.execute_write(import_equipment, row)

    logger.info("Neo4j 적재 완료!")



# 쿼리에는 쿼리 함수만 두고 데이터는 여기에서 처리하기 위해 파일을 분리함 
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)


    ############################################################
    # 데이터 가져오기 
    ############################################################
    df = pd.read_csv('Neo4j\\data\\Item_Equipment_cleaned.csv')
    logger.info('=== 로드된 데이터 확인 ===')
    logger.info(df.columns.tolist())
    logger.info(df.shape)

    ############################################################
    # 서버에 데이터 적제 
    ############################################################
    main(df)