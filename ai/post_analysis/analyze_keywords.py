"""Kiwi 형태소 분석으로 `analysis` 테이블의 `keywords` 열을 채운다."""

# 로그
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 패키지
import pandas as pd
from kiwipiepy import Kiwi

# 모듈
from common.constant import (
    AnalysisColumn,
    AnalyzeKeywordsConfig,
    CodeTable,
    KiwiPosTagPrefix,
    KeywordFormat,
)
from common.errors import PostAnalysisErrors
from postgresql.run_query import get_analysis_data, merge_analysis_data

#########################################


def analyze_keywords() -> None:
    """`keywords`가 비어 있는 행만 조회해 명사·동사 계열 토큰을 `#`로 잇고 MERGE로 반영한다.

    ``information_cd`` 가 IC02(IT 정보)인 행은 제외한다.
    """

    # 형태소 분석기
    kiwi = Kiwi()

    # 데이터 로드 (데이터 로드 부분을 데이터에서 서버 쿼리로 변경 )
    df = get_analysis_data()

    kw_col = AnalysisColumn.KEYWORDS.value
    content_col = AnalysisColumn.CONTENT.value
    info_col = AnalysisColumn.INFORMATION_CD.value

    if info_col not in df.columns:
        raise ValueError(PostAnalysisErrors.KiwiKeywords.missing_columns(info_col))
    df = df[df[info_col] != CodeTable.INFORMATION_IT_INFO.value]

    # 이미 키워드가 존재하는 경우 처리할 데이터에서 제외 (키워드 없는 데이터만 선택함)
    df = df[df[kw_col].isnull()]
    
    # 빈 칸만 있으면 keywords 열이 float64로 잡혀 문자열 대입 시 오류가 난다.
    df[kw_col] = df[kw_col].astype(AnalyzeKeywordsConfig.DTYPE_OBJECT)

    tag_prefixes = tuple(p.value for p in KiwiPosTagPrefix)

    # 데이터에서 content 컬럼 값을 가져와서 row 별로 형태소 분석 진행한 뒤 keywords 컬럼에 적용한다. 
    for index, row in df.iterrows():
        text = row[content_col]
        tokens = kiwi.analyze(text)[0][0]
        keywords = [
            token.form
            for token in tokens
            if any(token.tag.startswith(p) for p in tag_prefixes)
        ]

        df.at[index, kw_col] = KeywordFormat.SEP.join(keywords).strip()
        logger.info(f"keywords: {keywords}")

    # 처리 결과 데이터를 다시 analysis 테이블에 업데이트 
    merge_analysis_data(df)

    logger.info("데이터 적용 완료")



########################################################
if __name__ == "__main__":
    analyze_keywords()
