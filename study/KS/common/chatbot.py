# 패키지
import time 

# 모듈
from .graphs import create_chatbot_graph
from .graphs import create_chatbot_graph_for_agent
from common.constants import LLM_NM

# LLM 관련 라이브러리 
from langchain_core.messages import HumanMessage

################################################################################
# 일반 쳇봇 응답용 함수 
################################################################################

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


################################################################################
# 에이전트 응답용 함수 
################################################################################

# 답변 응답 함수 
def get_msg_from_agent(llm:str=LLM_NM.ollama.name, user_input:str=''):

    graph = create_chatbot_graph_for_agent()

    # 에이전트 실행
    result = graph.invoke({
        "messages": [HumanMessage(content=user_input)],
        "llm": llm
    })
    outputs = result['messages'][-1].content
    
    for output in outputs:
        yield output
        time.sleep(0.05)