################################################################################
# 필요한 라이브러리 호출
################################################################################

# 패키지
import streamlit as st

# 모듈
from common.agents import get_msg_from_agent
from common.utils import check_tavily_history, render_tavily_history

# LLM 관련 라이브러리
from langchain_core.messages import HumanMessage, AIMessage

################################################################################
# streamlit 화면 구성 
################################################################################

# 타이틀
st.title('Tavily Search Agent')

# 대화기록 세션에 저장 (세션에 없으면 빈 리스트로 추가함 )
check_tavily_history()

# 과거 대화내용 화면에 순차적으로 표시 (이전 대화상황 랜더랑 )
render_tavily_history()



################################################################################
# 화면 동작 
################################################################################

# 사용자 입력 
if user_input := st.chat_input('날씨가 궁금한 도시이름을 포함해서 질문해주세요.'):

    # 사용자 메시지
    with st.chat_message('user'):
        st.write(user_input)

    # LLM 답변 (토큰 단위로 날아오면 stream 해서 표시 )
    with st.chat_message("assistant"):
        placeholder = st.empty()
        response = ''
        for token in get_msg_from_agent(user_input):
            response += token
            placeholder.markdown(response)

    # 대화기록 세션에 추가 (사람 메시지 -> AI 답변 순서로 )
    st.session_state.tavily_messages.append(HumanMessage(content=user_input))
    st.session_state.tavily_messages.append(AIMessage(content=response))






