'''
스테이트
- 유저입력
- 사용할 모델 또는 모델 이름 
- 키워드 (초기값 없음 -> 중간에 생성)
- 메시지 출력 

1. 사용자 질문을 바탕으로 키워드 생성
-> coding, cooking, general

2-1. 만약 coding이면 coding 체인으로 
2-2. 만약 cooking이면 cooking 체인으로 
2-3. 만약 general이면 general 체인으로 

3. 그렇게 나온 체인 결과를 사용자에게 전달. 
'''

from .state import ChatbotState
from .node import create_keyword_node, create_coding_node, create_cooking_node, create_general_node
from .agents import create_keyword_for_agent, create_agent_by_weather, create_agent_by_news, create_agent_by_stock
from langgraph.graph import StateGraph, END, START


############################################################
# 일반 쳇봇 용 컨디션 분기 / 그래프 생성 
############################################################

# 키워드를 가지고 질문을 분기하는 노드 
def route_by_keyword(state: ChatbotState) -> str:
    """
    질문 유형에 따라 어떤 노드로 갈지 결정하는 함수
    """

    keyword = state.get("keyword", "general") # 키워드 값이 있으면 키워드를 사용 / 아니면 일반 
    
    node_name = 'create_general_node'

    if keyword == "coding":
        node_name = 'create_coding_node'
    elif keyword == "cooking":
        node_name = 'create_cooking_node'

    return node_name


def create_chatbot_graph():
    """
    조건부 엣지가 있는 키워드 기반 질문 답변 챗봇 
    """
    ##################################################
    # 그래프를 생성할 객체 생성   
    ################################################## 
    workflow = StateGraph(ChatbotState)
    
    ##################################################
    # 모든 노드 추가
    ##################################################
    workflow.add_node("create_keyword_node", create_keyword_node)
    workflow.add_node("create_coding_node", create_coding_node)
    workflow.add_node("create_cooking_node", create_cooking_node)
    workflow.add_node("create_general_node", create_general_node)
    
    ##################################################
    # 모든 엣지 추가 
    ##################################################
    # 시작점: 질문 분석부터
    # workflow.set_entry_point("analyze")
    workflow.add_edge(START, "create_keyword_node")
    
    # 조건부 엣지: 분석 결과에 따라 분기
    workflow.add_conditional_edges(
        "create_keyword_node",  # 어떤 노드에서
        route_by_keyword,  # 어떤 함수로 결정하고
        {
            "create_coding_node": "create_coding_node",
            "create_cooking_node": "create_cooking_node",
            "create_general_node": "create_general_node"
        }  # 가능한 다음 노드들
    )
    
    # 모든 응답 노드는 종료점
    # workflow.set_finish_point("answer_coding")
    # workflow.set_finish_point("answer_cooking")
    # workflow.set_finish_point("answer_general")
    workflow.add_edge("create_coding_node", END)
    workflow.add_edge("create_cooking_node", END)
    workflow.add_edge("create_general_node", END)

    ##################################################
    # 컴파일 -> 그래프 생성  
    ################################################## 
    return workflow.compile()



############################################################
# 에이전트 쳇봇 용 컨디션 분기 / 그래프 생성 
############################################################

# 키워드를 가지고 질문을 분기하는 함수
def route_by_keyword_for_agent(state: ChatbotState) -> str:
    """
    질문 유형에 따라 어떤 에이전트를 실행할 지 결정하는 함수
    """

    keyword = state.get("keyword", "weather_agent") # 키워드 값이 있으면 키워드를 사용 / 아니면 일반 
    agent_name = 'create_agent_by_weather'

    if keyword == "news_agent":
        agent_name = 'create_agent_by_news'
    elif keyword == "stock_agent":
        agent_name = 'create_agent_by_stock'

    return agent_name

def create_chatbot_graph_for_agent():
    """
    조건부 엣지가 있는 키워드 기반 질문 답변 챗봇 
    """
    ##################################################
    # 그래프를 생성할 객체 생성   
    ################################################## 
    workflow = StateGraph(ChatbotState)
    
    ##################################################
    # 모든 노드 추가
    ##################################################
    workflow.add_node("create_keyword_for_agent", create_keyword_for_agent)
    workflow.add_node("create_agent_by_weather", create_agent_by_weather)
    workflow.add_node("create_agent_by_news", create_agent_by_news)
    workflow.add_node("create_agent_by_stock", create_agent_by_stock)
    
    ##################################################
    # 모든 엣지 추가 
    ##################################################
    # 시작점: 질문 분석부터
    # workflow.set_entry_point("analyze")
    workflow.add_edge(START, "create_keyword_for_agent")
    
    # 조건부 엣지: 분석 결과에 따라 분기
    workflow.add_conditional_edges(
        "create_keyword_for_agent",  # 어떤 노드에서
        route_by_keyword_for_agent,  # 어떤 함수로 결정하고
        {
            "create_agent_by_weather": "create_agent_by_weather",
            "create_agent_by_news": "create_agent_by_news",
            "create_agent_by_stock": "create_agent_by_stock"
        }  # 가능한 다음 노드들
    )
    
    # 모든 응답 노드는 종료점
    # workflow.set_finish_point("answer_coding")
    # workflow.set_finish_point("answer_cooking")
    # workflow.set_finish_point("answer_general")
    workflow.add_edge("create_agent_by_weather", END)
    workflow.add_edge("create_agent_by_news", END)
    workflow.add_edge("create_agent_by_stock", END)

    ##################################################
    # 컴파일 -> 그래프 생성  
    ################################################## 
    return workflow.compile()