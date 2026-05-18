"""LLM으로 `keywords`를 긍정·부정 키워드 컬럼으로 나누어 `analysis`에 저장한다."""

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
from common.constant import AnalysisColumn, ClassifyKeywordsConfig, CodeTable
from common.postgresql.run_query import get_analysis_data, merge_analysis_data

class KeywordClassification(BaseModel):
    """LangChain 출력 파싱용: 하나의 키워드 문자열을 긍·부정 두 줄로 분리한다."""

    positive_kw: str = Field(default="", description="긍정 키워드, #로 구분")
    negative_kw: str = Field(default="", description="부정 키워드, #로 구분")


def classify_sentimental_keywords() -> None:
    """미분류 행만 대상으로 LLM 체인을 실행하고 `positive_kw`·`negative_kw`를 MERGE한다."""
    kw_col = AnalysisColumn.KEYWORDS.value
    info_col = AnalysisColumn.INFORMATION_CD.value
    pos_col = AnalysisColumn.POSITIVE_KW.value
    neg_col = AnalysisColumn.NEGATIVE_KW.value

    # 데이터 로드 (해당 부분 이제 DB 읽어서 처리해도 됨)
    df = get_analysis_data()

    missing_cols = [
        c
        for c in (kw_col, info_col, pos_col, neg_col)
        if c not in df.columns
    ]
    if missing_cols:
        raise ValueError(
            "analysis 데이터에 키워드 분류에 필요한 컬럼이 없습니다: "
            + ", ".join(missing_cols)
        )

    # IT 정보(IC02, information_cd) 글 제외 — category_cd 축과 별개
    df = df[df[info_col] != CodeTable.INFORMATION_IT_INFO.value]

    # 이미 데이터가 존재하는 row 는 제외 
    df = df[df[pos_col].isnull() & df[neg_col].isnull()]

    # 테스트를 위해 4개 열만 처리 
    df = df.head(ClassifyKeywordsConfig.PREVIEW_MAX_ROWS)

    # 체인 구성 
    llm = ChatOpenAI(model=ClassifyKeywordsConfig.OPENAI_MODEL)
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
    input_variables=[kw_col],
    partial_variables={
        "format_instructions": parser.get_format_instructions(),
    },
)

    # 체인 실행 
    chain = prompt | llm | parser

    for index, row in df.iterrows():
        result = chain.invoke({kw_col: row[kw_col]})
        logger.info(result)
        df.at[index, pos_col] = result.positive_kw
        df.at[index, neg_col] = result.negative_kw

    # 분류 컬럼 전처리 
    # => 앞뒤 공백 제거 
    df[pos_col] = df[pos_col].str.strip()
    df[neg_col] = df[neg_col].str.strip()

    # 처리 결과 데이터를 다시 analysis 테이블에 업데이트 
    merge_analysis_data(df)
    logger.info("키워드 분류 완료")

if __name__ == "__main__":
    classify_sentimental_keywords()
