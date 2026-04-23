# 환경변수 
from dotenv import load_dotenv
load_dotenv()

# 로그 
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 패키지
import streamlit as st

# 모듈
from src.screen.display import print_message
from src.screen.history import init_history
from src.components.sidebar import chatbot_sidebar
from src.langgraph.run import response_from_graph

# DB 커넥션 
from src.postgresql.connection import check_connection


##############################################################################################
# 시작 시 연결 체크 
##############################################################################################
check_connection() # 시작시 해당 함수를 1번 호출해서 연결 테스트를 진행한다. 


##############################################################################################
# 쳇봇 화면 
##############################################################################################

st.title('Chatbot')                 # 제목 
model = chatbot_sidebar()          # 사이드 바
init_history()                      # 히스토리


#########################################################
# 사용자 메시지
#########################################################
question = st.chat_input('질문을 입력하세요.')
if question is not None:                                                    
    user_msg = {'role': 'user', 'content': question}                        # 사용자 입력 내용 (한번에 받음 )
    print_message(**user_msg)

    #########################################################
    # LLM 메시지 
    #########################################################
    response = response_from_graph(user_msg=user_msg['content'], model=model)
    ai_msg = {'role': 'assistant', 'content': response}                     # ai 답변 내용 (chain.invoke 결과 출력 )
    print_message(**ai_msg)

    #########################################################
    # 채팅 이력 추가 (사람 -> Ai 순으로 ) 
    #########################################################
    st.session_state.messages.append(user_msg)
    st.session_state.messages.append(ai_msg)




