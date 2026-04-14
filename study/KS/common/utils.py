# 패키지
import streamlit as st


############################################################
# app.py 화면 랜더링
############################################################
def render_chat_history():
    '''
    app.py 화면에서 과거 메시지 내용을 순서대로 반환 
    '''
    for msg in st.session_state.messages:
        st.chat_message(msg.type).write(msg.content)


def check_chat_history():
    '''
    messages 세션이 없으면 빈 리스트로 추가하는 함수 
    '''
    if 'messages' not in st.session_state:
        st.session_state.messages = []

############################################################
# tavily.py 화면 랜더링
############################################################
def render_tavily_history():
    '''
    tavily.py 화면에서 과거 메시지 내용을 순서대로 반환 
    '''
    for msg in st.session_state.tavily_messages:
        st.chat_message(msg.type).write(msg.content)


def check_tavily_history():
    '''
    tavily_messages 세션이 없으면 빈 리스트로 추가하는 함수 
    '''
    if 'tavily_messages' not in st.session_state:
        st.session_state.tavily_messages = []
