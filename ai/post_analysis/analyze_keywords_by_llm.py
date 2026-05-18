"""OpenAI LLM으로 본문과 감성에 맞는 키워드 문자열을 추출해 `analysis`에 반영한다."""

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
from common.constant import AnalysisColumn, AnalyzeKeywordsByLlmConfig, CodeTable
from common.postgresql.run_query import get_analysis_data, merge_analysis_data

class Keywords(BaseModel):
    """LangChain `PydanticOutputParser`용 스키마: 키워드 문장들을 한 문자열(`#` 구분)로 받는다."""

    keywords: str = Field(default="", description="2~3단어 정도의 짧은 문장들을 #으로 연결한 하나의 스트링 값")


def analyze_keywords_by_llm(max_rows: int | None = None) -> None:
    """빈 본문을 제외한 뒤, 감성·본문을 입력으로 체인을 돌려 `keywords`를 채우고 DB에 MERGE한다.

    IC02(IT 정보, ``information_cd``) 행은 제외한다.

    Args:
        max_rows: 처리할 최대 행 수. ``None``이면 필터 후 전체. Lambda 등에서 타임아웃 방지용 청크에 사용.
    """

    # 데이터 로드 (데이터 로드 부분을 데이터에서 서버 쿼리로 변경 )
    df = get_analysis_data()

    content_col = AnalysisColumn.CONTENT.value
    kw_col = AnalysisColumn.KEYWORDS.value
    info_col = AnalysisColumn.INFORMATION_CD.value
    sent_col = AnalysisColumn.SENTIMENTAL.value
    title_col = AnalysisColumn.TITLE.value

    # content가 비어있는 경우 오류가 나기 때문에 제외
    empty_map = {k: pd.NA for k in AnalyzeKeywordsByLlmConfig.CONTENT_EMPTY_PLACEHOLDERS}
    c = df[content_col].replace(empty_map)
    df = df[c.notna() & c.astype(str).str.strip().ne("")]

    if info_col not in df.columns:
        raise ValueError(
            "analysis 데이터에 LLM 키워드 추출에 필요한 컬럼이 없습니다: "
            + info_col
        )
    df = df[df[info_col] != CodeTable.INFORMATION_IT_INFO.value]

    # 이미 키워드가 존재하는 경우 처리할 데이터에서 제외 (키워드 없는 데이터만 선택함)
    df = df[df[kw_col].isnull()]

    if df.empty:
        logger.info("모든 row에 키워드가 존재합니다. 처리할 데이터가 없습니다.")
        return

    # 빈 칸만 있으면 keywords 열이 float64로 잡혀 문자열 대입 시 오류가 난다.
    df[kw_col] = df[kw_col].astype(AnalyzeKeywordsByLlmConfig.DTYPE_OBJECT)

    if max_rows is not None and max_rows > 0:
        df = df.head(max_rows)

    # 체인 구성 
    llm = ChatOpenAI(model=AnalyzeKeywordsByLlmConfig.OPENAI_MODEL)

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
    input_variables=[content_col, sent_col],
    partial_variables={
        "format_instruction": parser.get_format_instructions()
    })
    chain = prompt | llm | parser

    # for문으로 content 컬럼 값을 가져와서 predict_sentiment 함수로 감성분석 진행 
    # 감성분석 결과를 sentimental, score 컬럼에 적용한다. 
    for index, row in df.iterrows():
        try:
            result = chain.invoke(
                {content_col: row[content_col], sent_col: row[sent_col]}
            )
            df.at[index, kw_col] = result.keywords
            logger.info(f"keywords: {result.keywords}")
        except Exception as e:
            logger.exception("행 %s 처리 실패 (index=%s)", row[title_col], index)
            continue


    # 처리 결과 데이터를 다시 analysis 테이블에 업데이트 
    merge_analysis_data(df)
    # df.to_csv("analyze_keywords_by_llm.csv", index=False)
    
    logger.info("키워드 추출 완료")



########################################################
if __name__ == "__main__":
    analyze_keywords_by_llm()
