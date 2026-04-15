# 패키지
import time 

# 모듈
from .graphs import create_chatbot_graph
from common.constants import LLM_NM

# LLM 관련 라이브러리 
from langchain_core.messages import HumanMessage

##########################################################################################
# 함수 정의 
##########################################################################################

def get_msg_from_graph(llm:str=LLM_NM.ollama.name, user_msg:str=''):
    '''
    사용자의 msg 받으면, llm 답변하는 함수
    - llm: 모델 종류
    - user_msg: 현재 사용자가 궁금한 질문 
    '''

    graph = create_chatbot_graph()

    # 답변 응답 
    answer =  graph.invoke({'messages':[HumanMessage(content=user_msg)], 'llm':llm})
    return answer['messages'][-1].content