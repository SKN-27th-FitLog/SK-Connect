from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
from typing import Generator
from src.core.config import settings
import logging

logger = logging.getLogger(__name__)

class DatabaseManager:
    """
    DB 연결 및 세션을 관리하는 클래스.
    설계안 5-3 (global mutable state 금지) 원칙 준수.
    """
    def __init__(self, db_url: str = None):
        self._db_url = db_url
        self._engine = None
        self._SessionLocal = None

    @property
    def engine(self):
        if self._engine is None:
            url = self._db_url or settings.database_url
            pool_args = {}
            if not url.startswith("sqlite"):
                pool_args = {
                    "pool_size": 5,
                    "max_overflow": 10,
                    "pool_pre_ping": True
                }

            self._engine = create_engine(
                url,
                echo=False,
                **pool_args
            )
        return self._engine

    @property
    def SessionLocal(self):
        if self._SessionLocal is None:
            self._SessionLocal = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=self.engine
            )
        return self._SessionLocal

    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        session = self.SessionLocal()
        try:
            yield session
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
