# 모듈
from .state import ChatbotState
from .constants import PROMPT_NM, LLM_NM, PARSER_NM
from .llm import get_llm, get_parser, get_prompt
from .tools import search_weather_info, summarize_news, search_stock_info

# LLM 관련 라이브러리
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage
from langchain.agents import create_agent
from langchain_tavily import TavilySearch


############################################################
# 에이전트 용 노드 함수 
############################################################
def create_keyword_for_agent(state: ChatbotState)-> ChatbotState:
    """사용자 질문을 바탕으로 키워드 체인 생성"""
    keyword_prompt = ChatPromptTemplate.from_messages([
        SystemMessage(content='''
        키워드를 파악하여 어떤 에이전트를 실행할 지 찾아서 반환해 주세요
        반환하는 값은 반드시 아래 4개 중에 하나여야 합니다. 
        - 뉴스에 대한 주제일 때 : news_agent
        - 날씨에 대한 주제일 때 : weather_agent
        - 주식에 대한 주제일 때 : stock_agent
        - 위 3개 주제 중 어디에도 속하지 않을 때 : weather_agent
        '''),
    ])
    
    keyword_chain = (keyword_prompt| get_llm(state['llm']) | get_parser(PARSER_NM.output_str.name))
    question = state['messages'][-1].content
    keyword = keyword_chain.invoke({'question': question})

    return {**state, "keyword": keyword} 

def create_agent_by_weather(state: ChatbotState)-> ChatbotState:
    """키워드가 날씨인 경우 실행하는 에이전트 노드 """

    agent = create_agent(
        model=get_llm(state['llm']),
        tools=[search_weather_info],
    )

    agent_chain = (
        agent
        | get_parser(PARSER_NM.output_str.name)
    )

    question = state['messages'][-1].content
    messages = [agent_chain.invoke({"messages": [HumanMessage(content=question)]})]
    return {**state, "messages": messages}

def create_agent_by_news(state: ChatbotState)-> ChatbotState:
    """키워드가 뉴스인 경우 실행하는 에이전트 노드 """
    agent = create_agent(
        model=get_llm(state['llm']),
        tools=[summarize_news],
    )

    agent_chain = (
        agent
        | get_parser(PARSER_NM.output_str.name)
    )

    question = state['messages'][-1].content
    messages = [agent_chain.invoke({"messages": [HumanMessage(content=question)]})]
    return {**state, "messages": messages}

def create_agent_by_stock(state: ChatbotState)-> ChatbotState:
    """키워드가 주식인 경우 실행하는 에이전트 노드 """
    agent = create_agent(
        model=get_llm(state['llm']),
        tools=[search_stock_info],
    )

    agent_chain = (
        agent
        | get_parser(PARSER_NM.output_str.name)
    )

    question = state['messages'][-1].content
    messages = [agent_chain.invoke({"messages": [HumanMessage(content=question)]})]
    return {**state, "messages": messages}