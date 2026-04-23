from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session, Session
from contextlib import contextmanager
from typing import Generator
from src.core.config import settings
import logging

logger = logging.getLogger(__name__)

class DatabaseManager:
    """
    DB 연결 및 세션을 관리하는 클래스.
    설계안 5-3 (global mutable state 금지) 등을 고려하여 객체화.
    """
    def __init__(self, db_url: str = settings.database_url):
        self.engine = create_engine(
            db_url,
            pool_size=5,             # Lambda 환경 고려하여 적절한 사이즈 설정
            max_overflow=10,
            pool_pre_ping=True,      # 연결 유효성 체크
            echo=False
        )
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine
        )

    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """
        세션을 안전하게 생성하고 반납하기 위한 컨텍스트 매니저.
        """
        session = self.SessionLocal()
        try:
            yield session
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

# 싱글톤으로 제공하되, 필요 시 인스턴스화 가능하도록 설계
db_manager = DatabaseManager()
