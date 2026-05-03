import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 패키지지
import pandas as pd
import time
from datetime import datetime

# 모듈
from common.postgresql.run_query import get_crawling_data, get_analysis_data, merge_analysis_data



def get_reviews():
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

    # 현재 시간 가져오기
    now = datetime.now().isoformat(timespec="seconds")

    # 테이블 데이터 가져오기
    df_crawling = get_crawling_data()
    df_analysis = get_analysis_data()

    # => df_analysis에서 crawling_id 컬럼값만 남김 
    df_analysis_created = df_analysis[["crawling_id"]]

    #################################################
    # 데이터 처리 
    #################################################

    # df_crawling에서 df_analysis_created 값과 같은 crawling_id가 있으면 드랍 (불리언 인덱싱)
    df_crawling_drop = df_crawling[~df_crawling["crawling_id"].isin(df_analysis_created["crawling_id"])]

    # df_crawling_drop 데이터를 analysis 테이블에 맞게 재설정 (컬럼별로 추가)
    df_analysis_new = pd.DataFrame()
    df_analysis_new["crawling_id"] = df_crawling_drop["crawling_id"]
    df_analysis_new["title"] = df_crawling_drop["title"]
    df_analysis_new["content"] = df_crawling_drop["content"]
    df_analysis_new["article_url"] = df_crawling_drop["article_url"]
    df_analysis_new["map_id"] = df_crawling_drop["map_id"]
    df_analysis_new["shop_id"] = df_crawling_drop["map_id"] # 맵이랑 샵id 동일 (나중에는 직접 쿼리로 찾아서 붙여야 함 )
    df_analysis_new["category_cd"] = df_crawling_drop["category_cd"]
    df_analysis_new["created_dt"] = now

    #################################################
    # 처리된 데이터를 analysis 테이블에 업데이트 
    #################################################
    merge_analysis_data(df_analysis_new)
    logger.info("데이터 적용 완료")


if __name__ == "__main__":
    get_reviews()