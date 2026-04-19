"""
config/settings.py — 프로젝트 전역 환경 설정

.env 파일에서 환경 변수를 로드하고,
모든 모듈이 참조할 수 있는 단일 설정 객체를 제공합니다.

[사용법]
    from config.settings import settings
    print(settings.NEO4J_URI)
    print(settings.OLLAMA_MODEL)

[설계 원칙]
- 환경 변수는 이 파일에서만 읽습니다 (Single Source).
- 각 모듈이 개별적으로 load_dotenv()를 호출하지 않습니다.
- 기본값(fallback)이 제공되어 .env 없이도 최소 동작이 가능합니다.
"""

import os
from dotenv import load_dotenv

# .env 파일을 프로젝트 루트에서 로드 (최초 1회)
load_dotenv()


class Settings:
    """
    프로젝트 전역 설정을 보관하는 불변 설정 클래스.

    속성:
        NEO4J_URI      : Neo4j Bolt 프로토콜 URI
        NEO4J_USER     : Neo4j 인증 사용자명
        NEO4J_PASSWORD : Neo4j 인증 비밀번호
        OLLAMA_MODEL   : Ollama LLM 모델명
        NUM_CTX        : LLM 컨텍스트 윈도우 크기 (토큰 수)
        RULES_FILE     : LLM 행동 규격서 파일 경로
        LOG_DIR        : 애플리케이션 로그 저장 디렉토리
        DB_DIR         : 런타임 DB 파일 저장 디렉토리
    """

    # ─── Neo4j 데이터베이스 ───────────────────
    NEO4J_URI: str = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    NEO4J_USER: str = os.getenv("NEO4J_USER", "neo4j")
    NEO4J_PASSWORD: str = os.getenv("NEO4J_PASSWORD", "password")

    # ─── LLM (Ollama) ────────────────────────
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "gemma3:4b")
    NUM_CTX: int = int(os.getenv("NUM_CTX", "8192"))

    # ─── 파일 경로 ───────────────────────────
    RULES_FILE: str = os.getenv("RULES_FILE", "RULE.MD")
    LOG_DIR: str = os.getenv("LOG_DIR", "logs")
    DB_DIR: str = os.getenv("DB_DIR", "database")

    # ─── Java (KoNLPy용, ingestion 전용) ─────
    JAVA_HOME: str = os.getenv("JAVA_HOME", "")


# 싱글톤 인스턴스: 프로젝트 전역에서 이 객체를 import하여 사용
settings = Settings()
