# 로그 
import logging
logger = logging.getLogger(__name__)

# 패키지 
import pandas as pd

# 모듈
from common.db.connenct_neo4j import get_neo4j_driver
from qurry_neo4j import import_equipment



    


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
    # 데이터 가져오기 
    ############################################################
    df = pd.read_csv('Neo4j\\data\\Item_Equipment_cleaned.csv')
    logger.info('=== 데이터 가져오기 ===')
    logger.info(df.columns.tolist())
    logger.info(df.shape)