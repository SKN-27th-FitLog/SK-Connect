# 패키지 
import streamlit as st

# 모듈 
from .llm import get_llm, get_parser, get_prompt
from .constants import PROMPT_NM, LLM_NM, PARSER_NM
from .state import ChatbotState

# LLM 관련 라이브러리 
from langchain_core.prompts import ChatPromptTemplate, HumanMessagePromptTemplate

##########################################################################################
# 체인 구성 
##########################################################################################

# 출력할 체인 생성 (과거 히스토리 포함)
def create_chain(
    prompt:str=PROMPT_NM.general.name, 
    state:ChatbotState=None,
    ):
    '''
    사용자 입력정보와 설정들을 가져와서 실행할 체인을 생성하는 함수 
    - prompt_nm: 프롬프트 종류
    - state: 그래프 상태 클래스 
    '''

    # 프롬프트 조립 (시스템 메시지, 사용자 메시지, 과거 대화 메시지)
    messages = [get_prompt(prompt)] + state["messages"]
    chat_prompt = ChatPromptTemplate.from_messages(messages=messages)


    # 조립된 체인 반환 
    return chat_prompt | get_llm(state['llm'])