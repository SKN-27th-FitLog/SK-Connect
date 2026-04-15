# 패키지
import hashlib
import base64
import os
import psycopg
import streamlit as st


#####################################################################################
# 암호화 키 생성 
#####################################################################################

def create_langgraph_secure_key(seed: str):
    '''
    암호화 키 생성 함수 
    
    Args:
        seed: 랜덤 시드값
        
    Returns:
        final_key: 암호화 키
    '''
    # 솔트는 고정값이 아닌 앱별로 안전하게 생성/보관되어야 함.
    salt_b64 = os.getenv("KDF_SALT_B64")
    if salt_b64:
        salt = base64.b64decode(salt_b64)
    else:
        salt = b"dev-salt-please-change"  # 개발용. 운영에서는 안전한 솔트 사용.

    # 1) PBKDF2: 강력한 KDF
    raw_key = hashlib.pbkdf2_hmac(
        hash_name="sha256",
        password=seed.encode(),
        salt=salt,
        iterations=100_000,
        dklen=32  # 32 bytes → AES-256
    )

    # 2) base64 URL-safe 문자열로 인코딩 (길이 약 44)
    b64 = base64.urlsafe_b64encode(raw_key).decode()

    # 3) LangGraph가 요구하는 32 글자로 제한
    final_key = b64[:32]

    return final_key




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


def _db_config_from_env() -> dict:
    return {
        "host": os.getenv("DB_HOST"),
        "port": os.getenv("DB_PORT"),
        "database": os.getenv("DB_NAME"),
        "user": os.getenv("DB_USER"),
        "password": os.getenv("DB_PASSWORD"),
    }

@st.cache_resource
def get_postgres_checkpointer():
    """PostgresSaver 단일 인스턴스(테이블 setup 포함). 그래프 compile에 전달."""
    from langgraph.checkpoint.postgres import PostgresSaver
    serde = get_encrypted_serde()
    saver = PostgresSaver(PostgreDB(_db_config_from_env()).get_conn(), serde=serde)
    saver.setup()
    return saver






