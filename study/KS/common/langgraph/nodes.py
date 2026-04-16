# 로그
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 모듈
from common.langgraph.state import ChatbotState
from common.langgraph.models import get_model
from common.utils.constants import PROMPT_NM, LLM_NM, PARSER_NM
from common.utils.get_costant import get_llm, get_parser, get_prompt


#########################################
# 입력된 내용을 가지고 답변하는 기본 노드 
#########################################
def chatbot_node(state:ChatbotState) -> ChatbotState:
    '''
    채팅 노드 함수
    해당 노드로 유저 입력이 추가된 상태에서 state가 들어오면 
    답변을 추가해서 리턴하는 역할을 한다. 
    parameters:
    - state: 채팅 상태
    returns:
    - state: 채팅 상태
    '''
    # 모델호출 -> 답변 invoke -> role과 묶어서 구성 -> state에 추가 
    model = get_model()
    response = model.invoke(state['messages']).content
    state['messages'].append(response)

    # 확인용 로그 
    logger.info(f"{state['messages'][-1]} -> {response}")

    return state

###################################################
# 사용자 질문을 가지고 키워드를 생성하는 노드 
###################################################
def create_keyword_node(state: ChatbotState)-> ChatbotState:
    """
    사용자 질문을 바탕으로 키워드 체인 생성
    질문을 가지고 LLM 이 분석해서 적합한 키워드 하나를 지정하게 됨 
    키워드는 마지막에 입력한 질문을 가지고 분석하며 어떤 키워드로도 정할 수 없을 경우 일반적인 채팅으로 처리됨 
    """
    keyword_chain = (
        get_prompt(PROMPT_NM.keyword.name) 
        | get_llm(state['llm']) 
        # | get_parser(PARSER_NM.output_str.name)
    )
    question = state['messages'][-1].content
    keyword = keyword_chain.invoke({'question': question})
    return {**state, "keyword": keyword, } 


###################################################
# 사용자 질문을 가지고 키워드를 생성하는 노드 
###################################################
def create_coding_node(state: ChatbotState)-> ChatbotState:
    """사용자 질문을 바탕으로 코딩 노드 생성  """
    messages = create_chain(PROMPT_NM.coding.name, state=state).invoke(state)
    return {**state, "messages": messages}

def create_cooking_node(state: ChatbotState)-> ChatbotState:
    """사용자 질문을 바탕으로 쿠킹 노드 생성  """
    messages = create_chain(PROMPT_NM.cooking.name, state=state).invoke(state)
    return {**state, "messages": messages}

