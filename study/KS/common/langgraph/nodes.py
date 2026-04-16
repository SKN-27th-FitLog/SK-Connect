# 로그
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 모듈
from common.langgraph.state import ChatbotState
from common.langgraph.models import get_model

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