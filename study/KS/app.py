import streamlit as st
from langchain_core.messages import HumanMessage, AIMessage
from common.chatbot import get_msg_from_llm
from common.constants import LLM_NM

############################################################

# 타이틀
st.title('chatbot')

# 사이드 바
with st.sidebar:
    st.title('Setup')
    llm_nm = st.selectbox('Model', list(LLM_NM.__members__.keys()))
    chat_type = st.selectbox('chatType', ['일반', '기본', 'fewshot'] )


# 대화기록 세션에 저장 (세션에 없으면 빈 리스트로 추가함 )
if 'messages' not in st.session_state:
    st.session_state.messages = [] 

# 과거 대화내용 화면에 순차적으로 표시 (이전 대화상황 랜더랑 )
for msg in st.session_state.messages:
    st.chat_message(msg.type).write(msg.content)

# 사용자 입력 
if user_input := st.chat_input('질문을 입력하세요'):

    # 사용자 메시지
    with st.chat_message('user'):
        st.write(user_input)

    # LLM 답변 (토큰 단위로 날아오면 stream 해서 표시 )
    with st.chat_message("assistant"):
        placeholder = st.empty()
        response = ''
        for token in get_msg_from_llm(llm_nm, chat_type, user_input):
            response += token
            placeholder.markdown(response)

    # 대화기록 세션에 추가 (사람 메시지 -> AI 답변 순서로 )
    st.session_state.messages.append(HumanMessage(content=user_input))
    st.session_state.messages.append(AIMessage(content=response))