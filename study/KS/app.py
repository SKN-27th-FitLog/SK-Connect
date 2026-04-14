# 패키지 
import streamlit as st

# LLM 관련 라이브러리 
from langchain_core.messages import HumanMessage, AIMessage
from common.chatbot import get_msg_from_llm
from components.sidebar import chatbot_sidebar
from common.utils import render_chat_history, check_chat_history

############################################################
# streamlit 화면 구성
############################################################

# 타이틀
st.title('chatbot')

# 사이드 바
llm_nm = chatbot_sidebar()

# 대화기록 세션 체크 
check_chat_history()

# 과거 대화내용 화면에 순차적으로 표시
render_chat_history()



############################################################
# 화면 동작 
############################################################

# 사용자 입력 
if user_input := st.chat_input('질문을 입력하세요'):

    # 사용자 메시지
    with st.chat_message('user'):
        st.write(user_input)

    # LLM 답변 (토큰 단위로 날아오면 stream 해서 표시 )
    with st.chat_message("assistant"):
        placeholder = st.empty()
        response = ''
        for token in get_msg_from_llm(llm_nm, user_input):
            response += token
            placeholder.markdown(response)

    # 대화기록 세션에 추가 (사람 메시지 -> AI 답변 순서로 )
    st.session_state.messages.append(HumanMessage(content=user_input))
    st.session_state.messages.append(AIMessage(content=response))