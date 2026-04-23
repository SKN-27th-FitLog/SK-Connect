import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    """
    Meal ETL v4 시스템 환경 설정
    .env 파일 또는 환경 변수로부터 값을 로드합니다.
    """
    # 1. DB 접속 정보
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_USER: str = "postgres"
    DB_PASSWORD: str = "password"
    DB_NAME: str = "sk_connect"

    # 2. 데이터 레이크 기반 경로
    # 기본값은 현재 워킹 디렉토리의 data_lake 폴더
    DATA_LAKE_ROOT: str = os.path.join(os.getcwd(), "data_lake")

    # 3. 운영 정책
    DAILY_TARGET_COUNT: int = 100
    RETRY_MAX_LIMIT: int = 5
    
    # 4. 로깅 설정
    LOG_LEVEL: str = "INFO"

    # 설정 파일 로드 규칙 (.env 지원)
    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8",
        extra="ignore"
    )

# 싱글톤 인스턴스 생성
settings = Settings()
