# 로그
import logging
logger = logging.getLogger(__name__)

# 모듈
from common.langgraph.state import ChatbotState
from common.langgraph.tools import search_weather_info, summarize_news, search_stock_info
from common.utils.constants import LLM_NM

# LLM 관련 라이브러리
from langchain_core.messages import HumanMessage
from langchain.agents import create_agent


############################################################
# 세부 주제에 따른 실행 노드 
############################################################
def create_agent_by_weather(state: ChatbotState)-> ChatbotState:
    """키워드가 날씨인 경우 실행하는 에이전트 노드 """

    agent = create_agent(
        model=LLM_NM[state['model']].value[1],
        tools=[search_weather_info],
    )

    question = state['messages'][-1].content
    response = agent.invoke({"messages": [HumanMessage(content=question)]})

    logger.info(f"weather: {response}")

    return {**state, "messages": response["messages"]}



def create_agent_by_news(state: ChatbotState)-> ChatbotState:
    """키워드가 뉴스인 경우 실행하는 에이전트 노드 """
    agent = create_agent(
        model=LLM_NM[state['model']].value[1],
        tools=[summarize_news],
    )

    question = state['messages'][-1].content
    response = agent.invoke({"messages": [HumanMessage(content=question)]})

    return {**state, "messages": response["messages"]}



def create_agent_by_stock(state: ChatbotState)-> ChatbotState:
    """키워드가 주식인 경우 실행하는 에이전트 노드 """
    agent = create_agent(
        model=LLM_NM[state['model']].value[1],
        tools=[search_stock_info],
    )

    question = state['messages'][-1].content
    response = agent.invoke({"messages": [HumanMessage(content=question)]})

    return {**state, "messages": response["messages"]}