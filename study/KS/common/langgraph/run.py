# 패키지
import streamlit as st

# LangChain 라이브러리
from langchain_core.messages import HumanMessage

# 모듈 
from common.langgraph.graph import create_chatbot_graph

def response_from_graph(user_msg:str):
    '''
    유저의 채팅 입력을 받아서 채팅 그래프를 실행한 뒤 답변을 반환하는 함수 
    parameters:
    - user_msg: 유저의 채팅 입력
    returns:
    - state['messages'][-1].content: 채팅 그래프의 마지막 메시지 내용
    '''
    # tread_id 설정 
    config = {'configurable': {'thread_id': st.session_state.thread_id}}

    # 채팅 그래프 객체 생성 
    chat_graph = create_chatbot_graph()

    # 채팅 그래프 실행 
    state = chat_graph.invoke({'messages': [HumanMessage(content=user_msg)]},config=config)

    return state['messages'][-1].content
