""" 실행함수, 기본 폴더위치 설정 """
# 로그 
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
# 환경변수 
from dotenv import load_dotenv
load_dotenv()

# 패키지
import pandas as pd
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field

# 모듈
from common.postgresql.run_query import get_analysis_data, merge_analysis_data

class KeywordClassification(BaseModel):
    positive_kw: str = Field(default="", description="긍정 키워드, #로 구분")
    negative_kw: str = Field(default="", description="부정 키워드, #로 구분")


def classify_sentimental_keywords():
    # 데이터 로드 (해당 부분 이제 DB 읽어서 처리해도 됨)
    df = get_analysis_data()

    # 데이터 중에서 IC02인 데이터 제외 (IC02는 키워드 분류 불가능한 데이터)
    df = df[df["category_cd"] != "IC02"]

    # 이미 데이터가 존재하는 row 는 제외 
    df = df[df["positive_kw"].isnull() & df["negative_kw"].isnull()]

    # 테스트를 위해 4개 열만 처리 
    df = df.head(4)

    # 체인 구성 
    llm = ChatOpenAI(model="gpt-5.4-nano")
    parser = PydanticOutputParser(pydantic_object=KeywordClassification)

    prompt = PromptTemplate(
        template="""당신은 키워드 분류 전문가 입니다. 
주어진 키워드 리스트를 긍정 키워드와 부정 키워드로 나누어주세요. 
각 키워드는 # 기호로 구분되어 있습니다. 예시: #키워드1#키워드2#키워드3

제시된 키워드를 읽고 아래 형태로 분류해 주세요. 
분류순서는 긍정키워드 => 부정키워드 순으로 위치해야 합니다. 

[키워드 목록]: 
{keywords}

[출력 형식]: 
{format_instructions}
""",
    input_variables=["keywords"],
    partial_variables={
        "format_instructions": parser.get_format_instructions(),
    },
)

    # 체인 실행 
    chain = prompt | llm | parser

    for index, row in df.iterrows():
        result = chain.invoke({"keywords": row["keywords"]})
        logger.info(result)
        df.at[index, "positive_kw"] = result.positive_kw
        df.at[index, "negative_kw"] = result.negative_kw

    # 분류 컬럼 전처리 
    # => 앞뒤 공백 제거 
    df["positive_kw"] = df["positive_kw"].str.strip()
    df["negative_kw"] = df["negative_kw"].str.strip()

    # 처리 결과 데이터를 다시 analysis 테이블에 업데이트 
    merge_analysis_data(df)
    logger.info("키워드 분류 완료")

if __name__ == "__main__":
    classify_sentimental_keywords()