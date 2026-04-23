import streamlit as st
from src.postgresql.connection import get_db_config_from_env, PostgreDB
from src.utils.serialize import get_encrypted_serde


# from langgraph.checkpoint.sqlite import SqliteSaver
# from common.db.connection import get_connection

# def get_checkpointer() -> object:
#     '''SQLite3 checkpointer 생성 함수'''
#     return SqliteSaver(conn=get_connection())



@st.cache_resource
def get_postgres_checkpointer():
    """PostgresSaver 단일 인스턴스(테이블 setup 포함). 그래프 compile에 전달."""
    from langgraph.checkpoint.postgres import PostgresSaver
    serde = get_encrypted_serde()
    saver = PostgresSaver(PostgreDB(get_db_config_from_env()).get_conn(), serde=serde)
    saver.setup()
    return saver