# 로그 
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 패키지
import pandas as pd
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field

# 모듈
from common.postgresql.run_query import get_analysis_data, merge_analysis_data

class Keywords(BaseModel):
    keywords: str = Field(default="", description="2~3단어 정도의 짧은 문장들을 #으로 연결한 하나의 스트링 값")


def analyze_keywords_by_llm():

    # 데이터 로드 (데이터 로드 부분을 데이터에서 서버 쿼리로 변경 )
    df = get_analysis_data()

    # content가 비어있는 경우 오류가 나기 때문에 제외 
    c = df["content"].replace({"": pd.NA, "-": pd.NA, "N/A": pd.NA})
    df = df[c.notna() & c.astype(str).str.strip().ne("")]

    # 이미 키워드가 존재하는 경우 처리할 데이터에서 제외 (키워드 없는 데이터만 선택함)
    df = df[df["keywords"].isnull()]
    
    # 빈 칸만 있으면 keywords 열이 float64로 잡혀 문자열 대입 시 오류가 난다.
    df["keywords"] = df["keywords"].astype("object")

    # # 테스트를 위해 4개 열만 처리 
    # df = df.head(6)

    # 체인 구성 
    llm = ChatOpenAI(model="gpt-5.4-mini")

    parser = PydanticOutputParser(pydantic_object=Keywords)

    prompt = PromptTemplate(
        template="""당신은 키워드 추출 전문가 입니다. 

주어진 글을 읽고 2~3단어 정도의 짧은 문장들을 추출해 주세요. 
추출할 문장은 제시된 감정분류를 고려해서 해당 의미를 담은 부분이어야 합니다. 

[글]: 
{content}

[감정분류]:
{sentimental}

[출력]: 
{format_instruction}

[제한사항]:
1. 추출할 문장은 2~3단어 정도의 짧은 문장이어야 합니다. 
2. 추출할 문장은 "sentimental"과 같은 방향성의 감정/의미를 담고 있어야 합니다. 
3. 절대로 "content"에 없는 새로운 단어나 글자를 생성하면 안됩니다. 
4. 추출된 문장들은 #으로 연결한 하나의 스트링 값으로 제공되어야 합니다. (예시: #음식이 맛있어요#가격이 저렴해요#사장님이 친절해요)

""",
    input_variables=["content", "sentimental"],
    partial_variables={
        "format_instruction": parser.get_format_instructions()
    })
    chain = prompt | llm | parser

    # for문으로 content 컬럼 값을 가져와서 predict_sentiment 함수로 감성분석 진행 
    # 감성분석 결과를 sentimental, score 컬럼에 적용한다. 
    for index, row in df.iterrows():
        try:
            result = chain.invoke(
                {"content": row["content"], "sentimental": row["sentimental"]}
            )
            df.at[index, "keywords"] = result.keywords
            logger.info(f"keywords: {result.keywords}")
        except Exception as e:
            logger.exception("행 %s 처리 실패 (index=%s)", row["title"], index)
            continue


    # 처리 결과 데이터를 다시 analysis 테이블에 업데이트 
    merge_analysis_data(df)
    # df.to_csv("analyze_keywords_by_llm.csv", index=False)
    
    logger.info("키워드 추출 완료")



########################################################
if __name__ == "__main__":
    analyze_keywords_by_llm()