# 로그
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 모듈 
from common.langgraph.state import ChatbotState
from common.langgraph.nodes import chatbot_node, create_keyword_node, create_coding_node, create_cooking_node
from common.langgraph.agents import create_agent_by_weather, create_agent_by_news, create_agent_by_stock
from common.db.checkpointer import get_postgres_checkpointer

# LangGraph 라이브러리 
from langgraph.graph import StateGraph, START, END

#################################################
# 그래프 분기 함수 
#################################################

def route_by_keyword(state: ChatbotState) -> str:
    """
    질문 유형에 따라 어떤 노드로 갈지 결정하는 함수
    """

    keyword = state["keyword"]
    
    # 키워드 로그 
    logger.info(f"keyword: {keyword}")

    # 노드 기본값 
    node_name = 'chatbot_node'

    if keyword == "coding":
        node_name = 'create_coding_node'
    elif keyword == "cooking":
        node_name = 'create_cooking_node'
    elif keyword == "weather":
        node_name = 'create_agent_by_weather'
    elif keyword == "news":
        node_name = 'create_agent_by_news'
    elif keyword == "stock":
        node_name = 'create_agent_by_stock'

    return node_name


#################################################
# 챗봇 그래프 생성 함수
#################################################
def create_chatbot_graph(is_checkpointer:bool=True):
    '''
    챗봇 그래프 생성 함수 
    parameters:
    - is_checkpointer: 체크포인터 사용 여부
    returns:
    - workflow: 챗봇 그래프
    '''
    # 그래프 정의 
    workflow = StateGraph(ChatbotState)
    
    # 노드 추가 
    workflow.add_node('create_keyword_node',        create_keyword_node)
    workflow.add_node('chatbot_node',               chatbot_node)
    workflow.add_node('create_coding_node',         create_coding_node)
    workflow.add_node('create_cooking_node',        create_cooking_node)
    workflow.add_node("create_agent_by_weather",    create_agent_by_weather)
    workflow.add_node("create_agent_by_news",       create_agent_by_news)
    workflow.add_node("create_agent_by_stock",      create_agent_by_stock)

    # 시작 앳지
    workflow.add_edge(START, 'create_keyword_node')

    # 조건부 엣지: 분석 결과에 따라 분기
    workflow.add_conditional_edges(
        "create_keyword_node",  # 어떤 노드에서
        route_by_keyword,  # 어떤 함수로 분기해서 
        {
            "chatbot_node"              : "chatbot_node",
            "create_coding_node"        : "create_coding_node",
            "create_cooking_node"       : "create_cooking_node",
            "create_agent_by_weather"   : "create_agent_by_weather",
            "create_agent_by_news"      : "create_agent_by_news",
            "create_agent_by_stock"     : "create_agent_by_stock",
        }  # 다음 노드들 중 하나로 결정된다. 
    )

    # 종료 앳지
    workflow.add_edge("create_coding_node", END)
    workflow.add_edge("create_cooking_node", END)
    workflow.add_edge('chatbot_node', END)
    workflow.add_edge('create_agent_by_weather', END)
    workflow.add_edge('create_agent_by_news', END)
    workflow.add_edge('create_agent_by_stock', END)


    # 그래프 컴파일
    if is_checkpointer:
        return workflow.compile(checkpointer=get_postgres_checkpointer())
    else:
        # LangGraph Studio 용 (외부 서버에서 돌고 있으므로 checkpointer 사용 안함 -> 주로 디버깅 용으로)
        return workflow.compile()

