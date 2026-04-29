""" 실행함수, 기본 폴더위치 설정 """
# 로그 
import logging
logging.basicConfig(level=logging.INFO)

# 패키지
import pandas as pd
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage
from dotenv import load_dotenv


class KeywordClassification(BaseModel):
    positive_kw: str = Field(default="", description="긍정 키워드, #로 구분")
    negative_kw: str = Field(default="", description="부정 키워드, #로 구분")



def main():

    # 데이터 로드 
    data = pd.read_csv("analysis_keywords.csv")
    df = pd.DataFrame(data)

    # 에러를 막기 위해 해당 컬럼값 오브젝트로 전환 
    df["keywords"] = df["keywords"].astype("object")
    df["positive_kw"] = df["positive_kw"].astype("object")
    df["negative_kw"] = df["negative_kw"].astype("object")

    # 체인 구성 
    llm = ChatOpenAI(model="gpt-5.4-nano")
    prompt = PromptTemplate(
        template=f"""당신은 키워드 분류 전문가 입니다. 
주어진 키워드 리스트를 긍정 키워드와 부정 키워드로 나누어주세요. 
각 키워드는 # 기호로 구분되어 있습니다. 예시: #키워드1#키워드2#키워드3
제시된 키워드를 읽고 아래 형태로 분류해 주세요. 분류순서는 긍정키워드 => 부정키워드 순으로 위치해야 합니다. 
만약 해당 분류가 없다면 "" (빈 문자열)로 적용해 주세요 
응답 결과는 "positive_kw": "키워드1#키워드2#키워드3", "negative_kw": "키워드4#키워드5#키워드6" 형식 으로만 표현되야 합니다. 

[키워드 목록]: {{keywords}}
[분류]: "positive_kw": "키워드1#키워드2#키워드3", "negative_kw": "키워드4#키워드5#키워드6"
"""
)

    parser = PydanticOutputParser(pydantic_object=KeywordClassification)

    chain = prompt | llm | parser

    # 체인 실행 
    for index, row in df.iterrows():
        result = chain.invoke({"keywords": row["keywords"]})
        print(result)
        df.at[index, "positive_kw"] = result.positive_kw
        df.at[index, "negative_kw"] = result.negative_kw

    # 결과 적용 
    df.to_csv("analysis_keywords_classified.csv", index=False)
    print("완료")

if __name__ == "__main__":
    load_dotenv()
    main()