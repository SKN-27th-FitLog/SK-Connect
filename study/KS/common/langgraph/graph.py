# 모듈 
from common.langgraph.state import ChatbotState
from common.langgraph.nodes import chatbot_node
from common.db.checkpointer import get_postgres_checkpointer

# LangGraph 라이브러리 
from langgraph.graph import StateGraph, START, END

#################################################
# 챗봇 그래프 생성 함수
#################################################
def create_chatbot_graph(is_checkpointer:bool=True):
    '''
    챗봇 그래프 생성 함수 
    '''
    # 그래프 정의 
    workflow = StateGraph(ChatbotState)
    
    # 노드 추가 
    workflow.add_node('chatbot_node', chatbot_node)

    # 앳지 추가 
    workflow.add_edge(START, 'chatbot_node')
    workflow.add_edge('chatbot_node', END)

    # 그래프 컴파일
    if is_checkpointer:
        return workflow.compile(checkpointer=get_postgres_checkpointer())
    else:
        # LangGraph Studio 용 (외부 서버에서 돌고 있으므로 checkpointer 사용 안함 -> 주로 디버깅 용으로)
        return workflow.compile()

