from .display import print_message
import streamlit as st
import uuid


########################################
# 채팅 히스토리 출력 
########################################
def init_history() -> None:
    '''
    채팅 내역을 화면에 출력하는 함수 
    '''
    # 채팅 내역이 없으면 초기화
    if 'messages' not in st.session_state:
        st.session_state.messages = []
        st.session_state.thread_id = str(uuid.uuid4())

    # 채팅 내역을 화면에 출력
    for message in st.session_state.messages:
        print_message(**message)