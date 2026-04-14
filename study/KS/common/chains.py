import streamlit as st

from langchain_core.runnables import RunnableBranch, RunnablePassthrough, RunnableLambda
from langchain_core.prompts import ChatPromptTemplate, HumanMessagePromptTemplate

from .llm import get_llm, get_parser, get_prompt
from .constants import PROMPT_NM, LLM_NM, PARSER_NM


##########################################################################################
# 체인 구성 
##########################################################################################

# 출력할 체인 생성 (과거 히스토리 포함)
def create_chain(
    llm:str=LLM_NM.ollama.name, 
    prompt:str=PROMPT_NM.general.name, 
    parser:str=PARSER_NM.output_str.name, 
    chat_prompt:str=None
    ):
    '''
    사용자 입력정보와 설정들을 가져와서 실행할 체인을 생성하는 함수 
    - llm_nm: 모델 종류
    - prompt_nm: 프롬프트 종류
    - parser_nm: 파서 종류
    - chat_prompt: 채팅 프롬프트
    '''

    # 프롬프트 조립 (시스템 메시지, 사용자 메시지, 과거 대화 메시지)
    system_message = get_prompt(prompt)
    human_message = HumanMessagePromptTemplate.from_template(template='{question}')
    hist_messages = st.session_state.messages # 이미 리스트라서 따로 리스트로 넣진 않음 
    
    messages = [system_message] + hist_messages + [human_message]
    chat_prompt = ChatPromptTemplate.from_messages(messages=messages)


    # 조립된 체인 반환 
    return chat_prompt | get_llm(llm) | get_parser(parser)


# 체인 생성 
def get_chain(inputs:dict):
    '''
    모델을 결정한 상태에서 실제 사용될 체인을 결정하는 함수 
    해당 함수 내에서 체인 생성 함수를 호출하게 됨 
    설정 값은 딕셔너리로 받기로 함 (inputs)
    - inputs['llm']: 모델 종류
    - inputs['question']: user_input
    '''

    # 키워드 체인
    keyword = (
        get_prompt(PROMPT_NM.keyword.name) 
        | get_llm(inputs['llm']) 
        | get_parser(PARSER_NM.output_str.name)
    )

    keyword_chain = RunnablePassthrough.assign(
        keyword=keyword,
        llm=lambda x: inputs['llm'],
    )

    # 결합한 체인 리턴 
    return keyword_chain | RunnableBranch(
            (
                lambda x: (x.get("keyword") or "").strip().lower() == PROMPT_NM.coding.name, 
                create_chain(inputs['llm'], PROMPT_NM.coding.name, PARSER_NM.output_str.name)
            ),
            (
                lambda x: (x.get("keyword") or "").strip().lower() == PROMPT_NM.cooking.name,
                create_chain(inputs['llm'], PROMPT_NM.cooking.name, PARSER_NM.output_str.name)
            ),
            create_chain(inputs['llm'], PROMPT_NM.general.name, PARSER_NM.output_str.name)
        )