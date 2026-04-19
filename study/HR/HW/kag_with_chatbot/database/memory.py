"""
database/memory.py — LangGraph SQLite 체크포인터 관리

대화 상태(AgentState)를 SQLite에 저장하고 복원하는
LangGraph 체크포인터를 초기화합니다.

[설계 원칙]
    - 모듈 레벨 side-effect 최소화: 팩토리 함수로 제공
    - 테스트 시 in-memory DB(:memory:)로 교체 가능
    - 커넥션 해제를 위한 close 함수 제공

[사용법]
    from database.memory import create_checkpointer
    memory, conn = create_checkpointer()
    app_graph = workflow.compile(checkpointer=memory)

    # 종료 시
    conn.close()
"""

import os
import sqlite3

from langgraph.checkpoint.sqlite import SqliteSaver
from config.settings import settings


def create_checkpointer(db_path: str = None) -> tuple:
    """
    SQLite 기반 LangGraph 체크포인터를 생성합니다.

    Args:
        db_path: SQLite DB 파일 경로.
                 None이면 config의 DB_DIR + "chat_history.db" 사용.
                 ":memory:"를 전달하면 인메모리 DB 사용 (테스트용).

    Returns:
        (SqliteSaver, sqlite3.Connection) 튜플.
        사용 완료 후 conn.close()를 호출해야 합니다.

    Side Effect:
        DB 디렉토리가 없으면 자동 생성합니다.
    """
    if db_path is None:
        db_dir = settings.DB_DIR
        os.makedirs(db_dir, exist_ok=True)
        db_path = os.path.join(db_dir, "chat_history.db")

    conn = sqlite3.connect(db_path, check_same_thread=False)
    memory = SqliteSaver(conn)

    return memory, conn
