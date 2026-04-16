# 로그 
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 패키지
import os
import psycopg
import streamlit as st


#####################################################################################


# import sqlite3

# __sqlite_connection = None

# def get_connection() -> object:
#     '''Database connection 생성 함수'''
#     global __sqlite_connection

#     # 채팅 메모리 데이터베이스 연결 객체 생성 
#     if __sqlite_connection is None:
#         __sqlite_connection = sqlite3.connect(
#             'chatbot_memory.db',
#             check_same_thread=False
#         )

#     return __sqlite_connection



#####################################################################################
# 싱글톤 패턴 
#####################################################################################

class Singleton(type):
	_instances = {}

	def __call__(cls, *args, **kwargs):
		if cls not in cls._instances:
			cls._instances[cls] = super(Singleton, cls)\
				.__call__(*args, **kwargs)
		return cls._instances[cls]

#####################################################################################
# PostgreSQL 연결 싱글톤 패턴 
#####################################################################################
class PostgreDB(metaclass=Singleton):
    '''
    PostgreSQL 연결 싱글톤 패턴 클래스
    
    Args:
        DB_CONFIG: PostgreSQL 연결 설정
        
    Returns:
        conn: PostgreSQL 연결 객체
    '''
    def __init__(self, DB_CONFIG:dict):
        # PostgreSQL 연결 설정
        DB_URI = f"postgresql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"

        self.conn = psycopg.connect(DB_URI, autocommit=True)

    def get_conn(self):
        return self.conn # 커넥션 객체 반환 

#####################################################################################
# 암호화된 직렬화 객체 생성 함수 
#####################################################################################

# 캐시 리소스 데코레이터 적용(함수 호출 결과를 캐시에 저장)
@st.cache_resource 
def get_encrypted_serde():
    # LANGGRAPH_AES_KEY는 이 함수 호출 전에 이미 설정되어 있어야 함
    from langgraph.checkpoint.serde.encrypted import EncryptedSerializer
    return EncryptedSerializer.from_pycryptodome_aes()


def get_db_config_from_env() -> dict:
    return {
        "host": os.getenv("DB_HOST"),
        "port": os.getenv("DB_PORT"),
        "database": os.getenv("DB_NAME"),
        "user": os.getenv("DB_USER"),
        "password": os.getenv("DB_PASSWORD"),
    }



@st.cache_resource
def check_connection():
    # 데이터베이스 연결
    db_config = {
        "host": os.getenv("DB_HOST"),
        "port": os.getenv("DB_PORT"),
        "database": os.getenv("DB_NAME"),
        "user": os.getenv("DB_USER"),
        "password": os.getenv("DB_PASSWORD")
    }

    ############################################################
    # PostgreSQL 연결확인 및 체크포인터 설정
    ############################################################

    # 싱글톤 패턴 동작 확인
    logger.info("=== 싱글톤 패턴 동작 확인 ===")
    conn1 = PostgreDB(db_config).get_conn()
    conn2 = PostgreDB(db_config).get_conn()

    logger.info("첫 번째 연결: %s", conn1)
    logger.info("두 번째 연결: %s", conn2)

    try: 
        if conn1 is conn2:
            logger.info("같은 연결인가? %s", conn1 is conn2)
            logger.info("싱글톤 패턴 적용 완료: 동일한 연결을 재사용합니다.")

    except Exception as e:
        logger.error(f"PostgreSQL 연결 실패: {e}")
        raise e
