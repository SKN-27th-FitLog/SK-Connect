from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    """
    애플리케이션 설정을 관리하는 클래스.
    .env 파일에서 값을 읽어옴.
    """
    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Database
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str = "admin"
    DB_USER: str = "admin"
    DB_PASS: str = "admin123"

    # Crawler Settings
    HEAD_MODE: bool = False
    
    # Storage Settings
    LAKE_ROOT_PATH: str = "diningcode_real_lake"

    @property
    def database_url(self) -> str:
        return f"postgresql+psycopg://{self.DB_USER}:{self.DB_PASS}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

settings = Settings()
