# 로그
import logging
logger = logging.getLogger(__name__)

# 모듈 
from common.utils.constants import LLM_NM

# LLM 관련 라이브러리 
from langchain_groq import ChatGroq
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI


#################################################
# LLM 모델 호출 
#################################################
def get_model() -> object:
    '''
    LLM 모델 선택 함수
    현재 버전에서는 ChatOpenAI 전용으로 만들되 나중에는 입력값을 받아서 선택할 수 있도록 할 예정임
    parameters:
    - model_name: 모델 이름
    returns:
    - model: 모델 객체
    '''
    model = ChatOpenAI(model='gpt-5-nano')

    return model