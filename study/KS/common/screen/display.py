# 로깅 설정
import logging
logger = logging.getLogger(__name__)

# 패키지 
import streamlit as st


########################################
# 화면에 채팅내용 표시 
########################################
def print_message(**message:dict) -> None:
    '''
    채팅 내용 입력 시 화면에 출력하는 함수 
    parameters:
    - role: 채팅 내용의 역할 (user, assistant)
    - message: 채팅 내용
    '''
    role = message.get('role', 'assistant')
    content = message.get('content', '')

    with st.chat_message(role): # 채팅 내용의 역할에 따라 채팅 메시지 출력
        st.markdown(content) # 채팅 내용 출력
        logger.info(f"{role}: {content}")


