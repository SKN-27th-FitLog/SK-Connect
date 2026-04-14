################################################################################
# 필요한 라이브러리 호출
################################################################################
# 패키지
from dotenv import load_dotenv
import time

# 모듈

# LLM 관련 라이브러리 
from langchain.tools import tool
from langchain.agents import create_agent
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.runnables import RunnablePassthrough, RunnableBranch

from langchain_tavily import TavilySearch
from langchain_openai import ChatOpenAI


################################################################################
# 관련 변수 선언, 데이터 로드
################################################################################

# 환경변수 로드
load_dotenv()

# 사용할 LLM 모델 선언
llm = ChatOpenAI(
    model="gpt-5-nano",
    reasoning_effort="high",        # 논리성 강화
)

# 날씨 정보 검색용 탬플릿 
search_weather = TavilySearch(
    max_results=3,
    topic="general",               # 또는 "news", "finance" 등
    include_answer=True,           # 답변 포함 여부
    include_raw_content=False,     # 원본 내용 포함 여부
    include_images=False,          # 이미지 포함 여부
    search_depth="advanced",          # "basic" 또는 "advanced"
    include_domains=[
        "https://weather.daum.net/",
        "https://www.weatheri.co.kr/" 
    ],
    exclude_domains=None            # 필요하면 제외 도메인 지정 가능
)

# 뉴스 검색 요약 탬플릿 
search_new = TavilySearch(
    max_results=3,
    topic="news",               # 또는 "news", "finance" 등
    include_answer=True,           # 답변 포함 여부
    include_raw_content=False,     # 원본 내용 포함 여부
    include_images=False,          # 이미지 포함 여부
    search_depth="advanced",          # "basic" 또는 "advanced"
    include_domains=[
        "https://news.naver.com/",
        "https://news.daum.net/"
    ],
    exclude_domains=None            # 필요하면 제외 도메인 지정 가능
)

# 주식 정보 탬플릿 
search_finance = TavilySearch(
    max_results=3,
    topic="finance",               # 또는 "news", "finance" 등
    include_answer=True,           # 답변 포함 여부
    include_raw_content=False,     # 원본 내용 포함 여부
    include_images=False,          # 이미지 포함 여부
    search_depth="advanced",          # "basic" 또는 "advanced"
    include_domains=[
        "https://kr.investing.com/equities/south-korea",
        "https://finance.naver.com/"
    ],
    exclude_domains=None            # 필요하면 제외 도메인 지정 가능
)


################################################################################
# tools 
################################################################################

# 날씨 정보 검색 tool 
@tool  
def search_weather_info(city: str) -> str:
    """특정 도시의 현재 날씨 정보를 검색합니다."""
    try:
        search_query = f"{city} 현재 날씨 기온"
        result_weather = search_weather.invoke(search_query)
        
        if not result_weather['answer'] or len(result_weather['results']) < 1:
            return f"'{city}'의 날씨 정보를 찾을 수 없습니다."
        
        # 첫 번째 결과에서 날씨 정보 추출
        weather_info = f"""
        {city} 날씨 정보:
        {result_weather['answer']}

        출처: {result_weather['results'][0]['url']}
        """
        
        return weather_info
        
    except Exception as e:
        return f"날씨 정보 검색 중 오류가 발생했습니다: {str(e)}"

# 뉴스 검색 요약 tool 
@tool
def summarize_news(topic: str) -> str:
    """특정 주제의 최신 뉴스를 검색하고 요약합니다."""
    try:
        # 검색 쿼리 생성
        search_query = f"{topic} 최신 뉴스 한국"
        
        # 검색 실행
        result_new = search_new.invoke(search_query)
        
        if not result_new['results']:
            return f"'{topic}'에 대한 뉴스를 찾을 수 없습니다."
        
        # 결과 요약
        summary = f"'{topic}' 관련 최신 뉴스 요약:\n\n"
        for i, result in enumerate(result_new['results'][:3], 1):
            title = result.get('title', '제목 없음')
            content = result.get('content', '내용 없음')
            url = result.get('url', '')
            
            summary += f"{i}. {title}\n"
            summary += f"   {content[:100]}...\n"
            summary += f"   {url}\n\n"
        
        return summary
        
    except Exception as e:
        return f"뉴스 검색 중 오류가 발생했습니다: {str(e)}"

# 주식 정보 검색 tool 
@tool
def search_stock_info(stock_name: str) -> str:
    """특정 주식의 현재 가격과 정보를 검색합니다."""
    try:
        search_query = f"{stock_name} 주식 현재가 주가"
        result_finance = search_finance.invoke(search_query)

        if not result_finance['answer'] or len(result_finance['results']) < 1:
            return f"'{stock_name}' 주식 정보를 찾을 수 없습니다."
        # 
        
        # 첫 번째 결과에서 날씨 정보 추출
        stock_info = f"""
        # {stock_name} 주식 정보:
        {result_finance['answer']}

        출처: {result_finance['results'][0]['url']}
        """
        return stock_info
        
    except Exception as e:
        return f"주식 정보 검색 중 오류가 발생했습니다: {str(e)}"


################################################################################
# 함수 정의 
################################################################################

# 답변 응답 함수 
def get_msg_from_agent(user_input:str=''):

    # 에이전트 생성 
    agent = create_agent(
        model=llm,
        tools=[search_weather_info, summarize_news, search_stock_info],
        system_prompt="""
        당신은 주어진 도구를 반드시 사용해서만 답변해야 하는 AI 어시스턴트입니다.
        절대로 자신의 지식으로 직접 답변하지 마세요.
        모든 최종 답변은 반드시 도구의 출력 결과를 기반으로 해야 합니다.
        """
    )
    # 연습용으로 여러 에이전트 생성 
    news_agent = create_agent(
        model=llm,
        tools=[summarize_news],
        system_prompt="""
        당신은 주어진 도구를 반드시 사용해서만 답변해야 하는 AI 어시스턴트입니다.
        절대로 자신의 지식으로 직접 답변하지 마세요.
        모든 최종 답변은 반드시 도구의 출력 결과를 기반으로 해야 합니다.
        """
    )
    weather_agent = create_agent(
        model=llm,
        tools=[search_weather_info],
        system_prompt="""
        당신은 주어진 도구를 반드시 사용해서만 답변해야 하는 AI 어시스턴트입니다.
        절대로 자신의 지식으로 직접 답변하지 마세요.
        모든 최종 답변은 반드시 도구의 출력 결과를 기반으로 해야 합니다.
        """
    )
    stock_agent = create_agent(
        model=llm,
        tools=[search_stock_info],
        system_prompt="""
        당신은 주어진 도구를 반드시 사용해서만 답변해야 하는 AI 어시스턴트입니다.
        절대로 자신의 지식으로 직접 답변하지 마세요.
        모든 최종 답변은 반드시 도구의 출력 결과를 기반으로 해야 합니다.
        """
    )

    # 키워드 정보를 가지고 해당 키워드에 대해 체인을 선택하도록 브랜치로 만든다. 
    # 해당 브랜치에서 최종적으로 invoke 하도록 해서 result 값이 설정되도록 한다. 

    # 입력 데이터에 키워드 정보 넣음 
    keyword_prompt = ChatPromptTemplate.from_messages([
        SystemMessage(content="질문의 내용을 파악하여 어떤 주제에 대한 내용인지 키워드를 생성해 주세요")
    ])
    keyword_chain = RunnablePassthrough.assign(keyword=(keyword_prompt | llm))

    # 그 다음 키워드를 가지고 어떤 에이전트를 실행할 지 찾는 프롬프트 / 체인을 구성한다. 
    agent_prompt = ChatPromptTemplate.from_messages([
        SystemMessage(content='''
        키워드를 파악하여 어떤 에이전트를 실행할 지 찾아서 반환해 주세요
        반환하는 값은 반드시 아래 4개 중에 하나여야 합니다. 
        - 뉴스에 대한 주제일 때 : news_agent
        - 날씨에 대한 주제일 때 : weather_agent
        - 주식에 대한 주제일 때 : stock_agent
        - 위 3개 주제 중 어디에도 속하지 않을 때 : agent
        '''),
        ('user', 'keyword : {keyword}'),
    ])
    agent_chain = RunnablePassthrough.assign(agent=(agent_prompt | llm))

    # RunnableBranch로 x['agent'] 값에 따라 분기하도록 체인 처리 
    branch_chain = RunnableBranch(
        (
            lambda x: x['agent'] == 'news_agent',
            news_agent
        ),
        (
            lambda x: x['agent'] == 'weather_agent',
            weather_agent
        ),
        (
            lambda x: x['agent'] == 'stock_agent',
            stock_agent
        ),
        agent
    ) 
    chain = keyword_chain | agent_chain | branch_chain


    # 에이전트 실행
    result = chain.invoke({"messages": [HumanMessage(content=user_input)]})
    outputs = result['messages'][-1].content
    
    for output in outputs:
        yield output
        time.sleep(0.05)