import streamlit as st
from typing import List, Dict
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage

def init_session_state() -> None:
    """
    세션 상태 키가 없는 경우 초기화합니다.
    """
    if "chat_history" not in st.session_state:
        st.session_state["chat_history"] = []
    
    if "fewshot_examples" not in st.session_state:
        st.session_state["fewshot_examples"] = [] # 딕셔너리 리스트: {"input": "", "output": ""}

def add_message(role: str, content: str) -> None:
    """
    대화 히스토리에 메시지를 추가합니다.
    """
    if role == "user":
        st.session_state["chat_history"].append(HumanMessage(content=content))
    else:
        st.session_state["chat_history"].append(AIMessage(content=content))

def clear_chat_history() -> None:
    """
    멀티턴 대화 히스토리를 초기화합니다.
    """
    st.session_state["chat_history"] = []

def update_fewshot_examples(examples: List[Dict[str, str]]) -> None:
    """
    세션 상태의 Few-shot 예시를 업데이트합니다.
    """
    st.session_state["fewshot_examples"] = examples

def get_fewshot_examples() -> List[Dict[str, str]]:
    """
    현재 저장된 Few-shot 예시를 반환합니다.
    """
    return st.session_state.get("fewshot_examples", [])
