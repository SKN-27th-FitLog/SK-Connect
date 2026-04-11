import os
from dotenv import load_dotenv

def load_env_vars() -> None:
    """
    .env 파일에서 환경변수를 로드합니다.
    """
    load_dotenv()

def get_env_var(key: str, default: str = "") -> str:
    """
    환경변수를 조회하거나 기본값을 반환합니다.
    """
    return os.getenv(key, default)
