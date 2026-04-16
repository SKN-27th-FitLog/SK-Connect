# 로그 
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 패키지
import hashlib
import base64
import os

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


if __name__ == '__main__':
    # 키값 모르면 해당 함수 실행해서 키값 구함 
    # 시드값 등은 일단 임시로 적용 / 나중에는 입력식 등으로 변경해야 함 

    # 랜덤 시드값 생성 
    seed = os.getenv("SECRET_SEED", "Development")
    # 암호화 키 생성 
    secure_key = create_langgraph_secure_key(seed)
    logger.info(f"암호화 키: {secure_key}")



