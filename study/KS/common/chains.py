import streamlit as st

from langchain_core.runnables import RunnableBranch, RunnablePassthrough, RunnableLambda
from langchain_core.prompts import ChatPromptTemplate, HumanMessagePromptTemplate

from .llm import get_llm, get_parser, get_prompt
from .constants import PROMPT_NM, LLM_NM, PARSER_NM


##########################################################################################
# 체인 구성 
##########################################################################################

# 체인 종류 선택 
def select_chain(llm_nm:str=LLM_NM.ollama.name, chat_type:str='일반', keyword:str=''):
    '''
    해당 함수를 만들어서 RunnableLambda로 넘겨보자 
    해당 함수는 get_chain 내에서 호출되도록 처리한다.
    keyword 체인 뒤에 해당 부분을 둬서 선택적으로 체인을 처리할 수 있도록 함수로 만드는게 목표 
    
    종류별 체인은 해당 함수 안에서 결정하도록 함 
    - llm_nm: 모델 종류
    - chat_type: 채팅 타입
    '''
    # 키워드 확인 함수 
    get_keyword = lambda x: (x.get("keyword") or "").strip().lower()

    # branch 체인 분기 
    branch_chain = RunnableBranch(
        (
            lambda x: get_keyword(x) == PROMPT_NM.coding.name, 
            create_chain(llm_nm, PROMPT_NM.coding.name, 'output_str')
        ),
        (
            lambda x: get_keyword(x) == PROMPT_NM.cooking.name, 
            create_chain(llm_nm, PROMPT_NM.cooking.name, 'output_str')
        ),
        create_chain(llm_nm, PROMPT_NM.general.name, 'output_str')
    )

    ######################################
    # 체인 종류 결정
    ######################################

    # 기본 체인 설정 
    chain = branch_chain

    # 채팅 타입에 따라 체인 선택
    if chat_type == '기본': # 히스토리 모르는 단답형 체인 
        chain = (
        get_prompt(PROMPT_NM.general.name) 
        | HumanMessagePromptTemplate.from_template(template='{question}')
        | get_llm(llm_nm) 
        | get_parser('output_str')
        )

    elif chat_type == 'fewshot': # 키워드 리스트만 반환하는 fewshot 체인
        chain = create_chain(llm_nm, PROMPT_NM.fewshot.name, 'output_str')
        

    return chain




# 출력할 체인 생성 (과거 히스토리 포함)
def create_chain(
    llm_nm:str=LLM_NM.ollama.name, 
    prompt_nm:str=PROMPT_NM.general.name, 
    parser_nm:str=PARSER_NM.output_str.name, 
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
    system_message = get_prompt(prompt_nm)
    human_message = HumanMessagePromptTemplate.from_template(template='{question}')
    hist_messages = st.session_state.messages # 이미 리스트라서 따로 리스트로 넣진 않음 
    
    messages = [system_message] + hist_messages + [human_message]
    chat_prompt = ChatPromptTemplate.from_messages(messages=messages)


    # 조립된 체인 반환 
    return chat_prompt | get_llm(llm_nm) | get_parser(parser_nm)


# 체인 생성 
def get_chain(llm_nm:str=LLM_NM.ollama.name, chat_type:str='일반'):
    '''
    모델을 결정한 상태에서 실제 사용될 체인을 결정하는 함수 
    해당 함수 내에서 체인 생성 함수를 호출하게 됨 
    - llm_nm: 모델 종류
    '''

    # 키워드 체인
    keyword = (
        get_prompt(PROMPT_NM.keyword.name) 
        | get_llm(llm_nm) 
        | get_parser('output_str')
    )

    keyword_chain = RunnablePassthrough.assign(
        keyword=keyword,
        llm_nm=lambda x: llm_nm,
        chat_type=lambda x: chat_type,
    )

    # 체인 함수 결합
    lambda_chain = RunnableLambda(
        lambda x: select_chain(
            x['llm_nm'],
            x['chat_type'],
            x['keyword'],
        )
    )

    # 결합한 체인 리턴 
    return keyword_chain | lambda_chain