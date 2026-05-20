import logging

import pandas as pd

from common.constant import ItNewsFilePrefix, Service, Stage, Status
from common.utils import build_csv_path, get_run_time, information_cd_for_path, save_csv
from common.preprocess import (
    cleaning_data_in_df,
    get_crawling_success_for_cleaning,
    separate_success_and_fail,
)

logger = logging.getLogger(__name__)


##############################################################
# 실행 함수 
##############################################################
def cleaning_threads(
    *,
    output_csv_prefix: str = ItNewsFilePrefix.DEFAULT,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """클리닝 단계 진입: raw success CSV 로드·전처리·cleaning CSV 저장.

    Note:
        함수 유형: F — 단계 오케스트레이션
        안전성: Level 2 — CSV 읽기·쓰기; DB 직접 쓰기 없음
        불변 규칙: `Service` 열거 소스별 1회 로드 후 concat
        부작용: `process=cleaning` success/fail CSV
    """

    # 현재 시간 생성 
    run_time = get_run_time()

    ##############################
    # 성공 데이터 조회 (process=raw, Service 열거별 1회씩 로드 후 concat)
    ##############################
    frames: list[pd.DataFrame] = []
    for service in Service:
        # `process=raw` 에서 이 소스의 `{service}_*.csv` 만 로드(소스마다 1회)
        part = get_crawling_success_for_cleaning(service)
        if not part.empty:
            frames.append(part)

    df = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

    if df.empty:
        logger.info("클리닝: 입력 0행")
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
            Stage.CLEANING,
            information_cd_for_path(df_success),
            output_csv_prefix,
            Status.SUCCESS,
            run_time,
        )
        save_csv(df_success, path_success)
        logger.info("클리닝: 성공 CSV %s (%d행)", path_success.resolve(), len(df_success))

    if not df_fail.empty:
        path_fail = build_csv_path(
            Stage.CLEANING,
            information_cd_for_path(df_fail),
            output_csv_prefix,
            Status.FAIL,
            run_time,
        )
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

