import logging
import re
from functools import lru_cache

import pandas as pd
from datetime import date, datetime, timedelta
from pathlib import Path

from common.constant import CrawlingConstant, PathConst, Stage, Status, Service
from common.utils import build_csv_path, get_last_success_date_by_thread_prefix, get_run_time, save_csv
from common.preprocess import (
    cleaning_data_in_df,
    get_success_threads,
    separate_success_and_fail,
    _filter_crawl_rows_for_cleaning,
)

logger = logging.getLogger(__name__)


##############################################################
# 실행 함수 
##############################################################
def cleaning_threads(
    *,
    cleaning_service: Service = Service.IT_NEWS.service,
    ) -> tuple[pd.DataFrame, pd.DataFrame]:
    """diagram 2단계: 성공 CSV 로드·필터 → 전처리 → success/fail CSV."""

    # 현재 시간 생성 
    run_time = get_run_time()

    ##############################
    # 성공 데이터 조회 (raw=crawling, 소스별 1회씩 + concat 후 필터)
    ##############################
    th_geek = get_last_success_date_by_thread_prefix("geeknews_")
    th_pt = get_last_success_date_by_thread_prefix("pytorch_")
    df_g = get_success_threads(Stage.CRAWLING, Service.GEEKNEWS)
    df_p = get_success_threads(Stage.CRAWLING, Service.PYTORCH)
    if df_g.empty and df_p.empty:
        logger.info("클리닝: 저장 생략(입력 0행)")
        return pd.DataFrame(), pd.DataFrame()
    _parts = [d for d in (df_g, df_p) if not d.empty]
    df = pd.concat(_parts, ignore_index=True) if _parts else pd.DataFrame()
    if "created_at" not in df.columns or "thread" not in df.columns:
        logger.warning("클리닝: created_at/thread 컬럼 없음 — 중단")
        return pd.DataFrame(), pd.DataFrame()
    df = _filter_crawl_rows_for_cleaning(df, th_geek=th_geek, th_pt=th_pt)
    if df.empty:
        logger.info("클리닝: 저장 생략(입력 0행)")
        return pd.DataFrame(), pd.DataFrame()

    ##############################
    # 데이터 전처리 
    ##############################
    df = cleaning_data_in_df(df)

    ##############################
    # 성공 / 실패 데이터 분할 
    ##############################
    df_success, df_fail = separate_success_and_fail(df)

    ##############################
    # 데이터 저장 
    ##############################
    if not df_success.empty:
        path_success = build_csv_path(
            Stage.CLEANING, cleaning_service, Status.SUCCESS, run_time
        )
        save_csv(df_success, path_success)
        logger.info("클리닝: 성공 CSV %s (%d행)", path_success.resolve(), len(df_success))

    if not df_fail.empty:
        path_fail = build_csv_path(Stage.CLEANING, cleaning_service, Status.FAIL, run_time)
        save_csv(df_fail, path_fail)
        logger.info("클리닝: 실패 CSV %s (%d행)", path_fail.resolve(), len(df_fail))

    return df_success, df_fail


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s [%(name)s] %(message)s",
    )

    df_success, df_fail = cleaning_threads()
    logger.info("클리닝: 요약 success=%d fail=%d", len(df_success), len(df_fail))
