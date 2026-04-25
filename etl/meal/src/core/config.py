from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import AliasChoices, Field
from typing import Optional
import sys

class Settings(BaseSettings):
    """
    애플리케이션 설정을 관리하는 클래스.
    설계안 13-3 (유연한 설정): 개별 필드 혹은 DATABASE_URL 통합 방식 모두 지원.
    """
    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # 1. 통합 URL 방식 (우선순위 높음)
    DATABASE_URL: Optional[str] = None

    # 2. 개별 필드 방식 (기본값 제공하여 선택적 입력 가능케 함)
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: Optional[str] = Field(None, validation_alias=AliasChoices('DB_NAME', 'DATA_DB_NAME', 'SERVICE_DB_NAME'))
    DB_USER: Optional[str] = None
    DB_PASS: Optional[str] = Field(None, validation_alias=AliasChoices('DB_PASS', 'DB_PASSWORD'))

    # Crawler Settings
    HEAD_MODE: bool = False
    LAKE_ROOT_PATH: str = "diningcode_real_lake"

    @property
    def database_url(self) -> str:
        """최종적으로 사용할 DB 접속 URL 반환"""
        url = self.DATABASE_URL
        
        # http 로 시작하면 설정을 무시하고 개별 필드 조합 방식을 사용하도록 유도 (NoSuchModuleError 방지)
        if url and url.startswith("http"):
            url = None

        if url:
            # sqlalchemy+psycopg 환경에 맞게 프로토콜 교정 (필요 시)
            if url.startswith("postgresql://") and not url.startswith("postgresql+psycopg://"):
                url = url.replace("postgresql://", "postgresql+psycopg://", 1)
            return url
        
        # 개별 필드 조합 방식
        if not all([self.DB_USER, self.DB_PASS, self.DB_NAME]):
            print("\n[!] 설정 오류: DATABASE_URL 혹은 개별 DB 설정(USER, PASS, NAME)이 필요합니다.\n")
            sys.exit(1)
            
        return f"postgresql+psycopg://{self.DB_USER}:{self.DB_PASS}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

try:
    settings = Settings()
except Exception as e:
    print(f"\n[!] 설정 로드 중 오류 발생: {e}\n")
    sys.exit(1)
