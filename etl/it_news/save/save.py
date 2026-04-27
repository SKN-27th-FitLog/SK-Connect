"""save 단계: 클리닝 산출 로드 → `crawling` INSERT → 성공/실패 CSV( diagram §3 )"""
import logging

import pandas as pd

from common.constant import CrawlingColumn, Service, Stage, Status
from common.postgresql.run_query import insert_crawling_batch, fetch_crawling_dataframe
from common.preprocess import get_success_threads
from common.utils import get_last_success_date, get_run_time, build_csv_path, save_csv

logger = logging.getLogger(__name__)

####################################
# 실행 함수 
####################################
def save_threads(
    *,
    save_service: Service = Service.IT_NEWS.service,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """diagram 3단계: 전처리 CSV 로드·필터 → 저장 → success/fail CSV."""


    ##############################
    # 실행 시간 및 마지막 수집일 조회 
    ##############################
    run_time = get_run_time()
    last_collected_at = get_last_success_date()


    ##############################
    # cleaning 성공 데이터 조회 
    ##############################
    df = get_success_threads(
        Stage.CLEANING, Service.IT_NEWS, last_collected_at=last_collected_at
    )
    if df.empty:
        logger.info("save: 저장 생략(입력 0행)")
        return pd.DataFrame(), pd.DataFrame()

    df = df.drop_duplicates(subset=[CrawlingColumn.THREAD.value], keep="last")

    ##############################
    # crawling 테이블 데이터 조회 -> thread 컬럼값 기준으로 확인해서 중복이 있으면 df에서 해당 row 드랍 처리 
    ##############################
    
    # db에서 데이터 조회 -> 데이터 프레임으로 반환 
    df_thread = fetch_crawling_dataframe(CrawlingColumn.THREAD)

    # df와 df_crawling에서 thread 컬럼값 기준으로 중복 확인 만약 중복이 있으면 df 컬럼에서 해당 row drop
    cond = df[CrawlingColumn.THREAD.value].isin(df_thread[CrawlingColumn.THREAD.value])
    df = df[~cond]

    ##############################
    # cleaning 테이블 일괄 INSERT 
    ##############################
    try:
        insert_crawling_batch(df)
        df_success, df_fail = df, pd.DataFrame()
    except Exception:
        logger.exception("save: crawling 일괄 INSERT 실패 — 전부 fail 처리")
        df_success, df_fail = pd.DataFrame(), df


    ##############################
    # save 성공/실패 데이터 저장 
    ##############################
    if not df_success.empty:
        path_success = build_csv_path(Stage.SAVE, save_service, Status.SUCCESS, run_time)
        save_csv(df_success, path_success)
        logger.info("저장: 성공 CSV %s (%d행)", path_success.resolve(), len(df_success))

    if not df_fail.empty:
        path_fail = build_csv_path(Stage.SAVE, save_service, Status.FAIL, run_time)
        save_csv(df_fail, path_fail)
        logger.info("저장: 실패 CSV %s (%d행)", path_fail.resolve(), len(df_fail))

    return df_success, df_fail


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    a, b = save_threads()
    logger.info("저장: 요약 success=%d fail=%d", len(a), len(b))
