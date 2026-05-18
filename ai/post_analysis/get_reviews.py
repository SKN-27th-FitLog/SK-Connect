"""`crawling`에만 있는 신규 행을 `analysis` 스키마로 옮겨 적재한다."""

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 패키지지
import pandas as pd
from datetime import datetime

# 모듈
from common.constant import AnalysisColumn, CodeTable, CrawlingColumn, GetReviewsConfig
from common.postgresql.run_query import get_crawling_data, get_analysis_data, merge_analysis_data



def get_reviews() -> None:
    """
    crawling 테이블에서 데이터를 가져와 analysis 테이블로 옮기는 함수
    1. crawling 테이블을 가져옴
    2. analysis 테이블의 crawling_id 컬럼값을 가져옴
    3. crawling 테이블의 데이터를 analysis 테이블 데이터에 맞게 데이터 프레임 조정
    4. crawling_id (analysis) 가 이미 존재하는 row는 drop (신규만 추가)
    5. created_dt 컬럼 값은 now로 설정 (입력되는 시간이 날짜임)
    6. 나머지 데이터는 설정에 맞춰서 merge 함 
    """
    ###################################################
    # 데이터 설정 
    ###################################################

    cid_crawl = CrawlingColumn.CRAWLING_ID.value
    cid_an = AnalysisColumn.CRAWLING_ID.value
    title_c, title_a = CrawlingColumn.TITLE.value, AnalysisColumn.TITLE.value
    content_c, content_a = CrawlingColumn.CONTENT.value, AnalysisColumn.CONTENT.value
    url_c, url_a = CrawlingColumn.ARTICLE_URL.value, AnalysisColumn.ARTICLE_URL.value
    map_c, map_a = CrawlingColumn.MAP_ID.value, AnalysisColumn.MAP_ID.value
    shop_a = AnalysisColumn.SHOP_ID.value
    cat_c, cat_a = CrawlingColumn.CATEGORY_CD.value, AnalysisColumn.CATEGORY_CD.value
    created_a = AnalysisColumn.CREATED_DT.value

    # 현재 시간 가져오기
    now = datetime.now().isoformat(timespec=GetReviewsConfig.ISOFORMAT_TIMESPEC)

    # 테이블 데이터 가져오기
    df_crawling = get_crawling_data()
    df_analysis = get_analysis_data()

    # => df_analysis에서 crawling_id 컬럼값만 남김 
    df_analysis_created = df_analysis[[cid_an]]

    #################################################
    # 데이터 처리 
    #################################################

    # df_crawling에서 df_analysis_created 값과 같은 crawling_id가 있으면 드랍 (불리언 인덱싱)
    df_crawling_drop = df_crawling[~df_crawling[cid_crawl].isin(df_analysis_created[cid_an])]

    # IT 스트림은 category_cd=CA07(ETL CategoryCdCode.ETC); analysis 적재 대상 제외 — 식당 리뷰 파이프라인 우선
    df_crawling_drop = df_crawling_drop[
        df_crawling_drop[cat_c] != CodeTable.CATEGORY_ETC.value
    ]

    # df_crawling_drop 데이터를 analysis 테이블에 맞게 재설정 (컬럼별로 추가)
    df_analysis_new = pd.DataFrame()
    df_analysis_new[cid_an] = df_crawling_drop[cid_crawl]
    df_analysis_new[title_a] = df_crawling_drop[title_c]
    df_analysis_new[content_a] = df_crawling_drop[content_c]
    df_analysis_new[url_a] = df_crawling_drop[url_c]
    df_analysis_new[map_a] = df_crawling_drop[map_c]
    df_analysis_new[shop_a] = df_crawling_drop[map_c] # 맵이랑 샵id 동일 (나중에는 직접 쿼리로 찾아서 붙여야 함 )
    df_analysis_new[cat_a] = df_crawling_drop[cat_c]
    df_analysis_new[created_a] = now

    #################################################
    # 처리된 데이터를 analysis 테이블에 업데이트 
    #################################################
    merge_analysis_data(df_analysis_new)
    logger.info("데이터 적용 완료")


if __name__ == "__main__":
    get_reviews()
