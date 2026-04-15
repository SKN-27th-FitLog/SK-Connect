# 패키지 
import time
import streamlit as st
import uuid
import os
from dotenv import load_dotenv

# 환경변수 설정
load_dotenv()

# 로깅 설정
import logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

# 모듈
from common.chatbot import get_msg_from_graph
from components.sidebar import chatbot_sidebar
from common.secure import PostgreDB
from common.secure import get_postgres_checkpointer

# LLM 관련 라이브러리 
from langchain_core.messages import HumanMessage, AIMessage

############################################################
# 전역 설정 호출 (환경변수, 데이터베이스 연결, 암호화 키 설정 등...)
############################################################

# 데이터베이스 연결
DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT"),
    "database": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD")
}

############################################################
# PostgreSQL 연결확인 및 체크포인터 설정
############################################################

# 싱글톤 패턴 동작 확인
logger.info("=== 싱글톤 패턴 동작 확인 ===")
conn1 = PostgreDB(DB_CONFIG).get_conn()
conn2 = PostgreDB(DB_CONFIG).get_conn()

logger.info("첫 번째 연결: %s", conn1)
logger.info("두 번째 연결: %s", conn2)
logger.info("같은 연결인가? %s", conn1 is conn2)
logger.info("싱글톤 패턴 적용 완료: 동일한 연결을 재사용합니다.")


############################################################
# 체크포인터 로드 
############################################################

get_postgres_checkpointer()



############################################################
# streamlit 화면 구성
############################################################

# 타이틀
st.title('chatbot')

# 사이드 바
llm_nm = chatbot_sidebar()

# 세션 id 설정 
if 'memory_id' not in st.session_state:
    st.session_state.memory_id = str(uuid.uuid4())

# 대화기록 세션 체크 
if 'messages' not in st.session_state:
    st.session_state.messages = []

# 과거 대화내용 화면에 순차적으로 표시
for msg in st.session_state.messages:
    st.chat_message(msg.type).write(msg.content)


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
        for token in get_msg_from_graph(llm_nm, user_input):
            response += token
            placeholder.markdown(response)

    # 대화기록 세션에 추가 (사람 메시지 -> AI 답변 순서로 )
    st.session_state.messages.append(HumanMessage(content=user_input))
    st.session_state.messages.append(AIMessage(content=response))