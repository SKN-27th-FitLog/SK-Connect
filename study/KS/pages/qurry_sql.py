################################################################################
# 필요한 라이브러리 호출
################################################################################
import streamlit as st
from dotenv import load_dotenv
import time

from sqlalchemy import create_engine
from langchain_community.utilities.sql_database import SQLDatabase
from langchain_openai import ChatOpenAI
from langchain_community.agent_toolkits.sql.toolkit import SQLDatabaseToolkit
from langchain.agents import create_agent
from langchain_core.messages import HumanMessage, AIMessage

################################################################################
# 관련 변수 선언, 데이터 로드
################################################################################

# 환경변수 로드
load_dotenv()

# 커넥션 객체 생성 
engine = create_engine('mysql+mysqlconnector://urstory:u1234@localhost:3306/Chinook')

# 데이터베이스 별로 지정 
db = SQLDatabase(engine=engine)

# 모델 설정
llm = ChatOpenAI(
    model="gpt-5-nano",
    reasoning_effort="high",        # 논리성 강화
)

# 에이전트용 툴킷 로드 > 툴들을 변수에 등록 
toolkit = SQLDatabaseToolkit(db=db, llm=llm)
tools = toolkit.get_tools()

# 에이전트 용 시스템 프롬프트 주입 
system_prompt = """
You are an agent designed to interact with a SQL database.
Given an input question, create a syntactically correct {dialect} query to run,
then look at the results of the query and return the answer. Unless the user
specifies a specific number of examples they wish to obtain, always limit your
query to at most {top_k} results.

You can order the results by a relevant column to return the most interesting
examples in the database. Never query for all the columns from a specific table,
only ask for the relevant columns given the question.

You MUST double check your query before executing it. If you get an error while
executing a query, rewrite the query and try again.

DO NOT make any DML statements (INSERT, UPDATE, DELETE, DROP etc.) to the
database.

To start you should ALWAYS look at the tables in the database to see what you
can query. Do NOT skip this step.

Then you should query the schema of the most relevant tables.
""".format(
    dialect=db.dialect, # 데이터베이스 종류(mysql)
    top_k=5,            # 최대 결과 수
)

################################################################################
# 사용할 함수 정의 
################################################################################

# 답변 응답 함수 
def get_msg_from_agent(user_msg:str=''):

    agent = create_agent(
        llm,
        tools,
        system_prompt=system_prompt,
    )

    # 유저 입력 및 스트리밍 처리 
    for step in agent.stream({
        "messages": [{"role": "user", "content": user_msg}]}, 
        stream_mode="values"
        ):
        yield step['messages'][-1].content
        time.sleep(0.05)

################################################################################
# streamlit 화면 구성 (채팅 내용으로 출력)
################################################################################

# 타이틀
st.title('SQL Query Agent')

# 대화기록 세션에 저장 (세션에 없으면 빈 리스트로 추가함 )
if 'query_sql_messages' not in st.session_state:
    st.session_state.query_sql_messages = [] 

# 사용자 입력 
if user_input := st.chat_input('알고싶은 내용을 질문해 주세요!'):

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
    st.session_state.query_sql_messages.append(HumanMessage(content=user_input))
    st.session_state.query_sql_messages.append(AIMessage(content=response))