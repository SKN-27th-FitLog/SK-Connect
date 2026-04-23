'''
상수나 타입에 따른 고정 값을 정의하기 위한 파일
고정된 데이터 들을 들고와야 하는 경우 해당 파일에서 선언한 클래스를 사용하도록 한다. 
또한 enum을 사용해서 뭔가 로드해야 하는 경우 다른 파일에서 get 함수를 만들고 해당 enum 의 값을 가져와서 설정했을 때 
정상인지 체크하는 부분을 따로 만들고 정상인 경우 설정값을 반환하도록 처리한다. 
'''
# 패키지 
import enum

# 모듈

# LLM 관련 라이브러리 
from langchain_groq import ChatGroq
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate, ChatPromptTemplate, FewShotChatMessagePromptTemplate
from langchain_core.messages import SystemMessage
from langchain_tavily import TavilySearch


################################################################################
# 상수, class 선언
################################################################################

# Model Class Enum
class LLM_NM(enum.Enum):
    ollama  = (enum.auto(), ChatOllama(model="gemma4:e2b"))
    groq    = (enum.auto(), ChatGroq(model="openai/gpt-oss-120b"))
    openai  = (enum.auto(), ChatOpenAI(model="gpt-4o"))
    gpt5    = (enum.auto(), ChatOpenAI(
        model="gpt-5-nano",
        reasoning_effort="high",        # 논리성 강화
    ))
    gpt5_4nano = (enum.auto(), ChatOpenAI(model="gpt-5.4-nano"))
    


# Prompt Template
class PROMPT_NM(enum.Enum):
    coding  = (enum.auto(), ChatPromptTemplate.from_template(template="IT 개발 전문가로서 다음 질문에 답변해주세요"))
    cooking = (enum.auto(), ChatPromptTemplate.from_template(template="요리 전문가로서 다음 질문에 답변해주세요"))
    general = (enum.auto(), ChatPromptTemplate.from_template(template="일반적인 질문에 답변해주세요"))
    keyword = (enum.auto(), ChatPromptTemplate.from_template(template=
        '''
        당신은 사용자의 질문을 분석하여 적절한 키워드를 생성하는 전문가 입니다. 
        다음 키워드 중 하나를 선택하여 반환하세요

        - coding : 프로그래밍이나 코딩과 관련된 질문인 경우
        - cooking : 요리에 대한 질문인 경우
        - weather : 날씨에 대한 질문이면서 특정 지역 / 도시를 같이 지정해서 질문한 경우
        - news : 뉴스기사에 대한 질문인 경우 
        - stock : 주식과 관련된 질문인 경우
        - general : 위 5개 주제 중 어디에도 속하지 않는 경우 (일반적인 질문)

        질문:{question}
        키워드:
        '''))

# Parser Type
class PARSER_NM(enum.Enum):
    output_str      = (enum.auto(), StrOutputParser())

class TavilySearch_NM(enum.Enum):
    # 날씨 정보 검색용 탬플릿 
    search_weather = (enum.auto(), TavilySearch(
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
    )
    # 뉴스 검색 요약 탬플릿 
    search_new = (enum.auto(), TavilySearch(
        max_results=3,
        topic="news",               # 또는 "news", 등
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
    )

    # 주식 정보 탬플릿 
    search_finance = (enum.auto(), TavilySearch(
        max_results=3,
        topic="finance",               # 또는 "finance" 등
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
    )

class TavilySearchParams():
    BASE_PARAMS =  {
        "max_results": 1,
        "include_answer": True,
        "include_raw_content": False,
        "include_images": False,
        "search_depth": "advanced",
        "include_domains": ["huggingface.co", "github.com"],
    }