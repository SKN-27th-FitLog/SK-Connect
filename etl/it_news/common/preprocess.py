# 패키지 
import pandas as pd
import re
from functools import lru_cache
import logging
from datetime import date, datetime, timedelta
from pathlib import Path

# 모듈
from common.constant import (
    CrawlingColumn,
    CrawlingConstant,
    PathConst,
    Service,
    Stage,
    Status,
)
from common.utils import (
    collect_crawling_success_datas,
    collect_save_stage_success_datas,
    get_last_success_date,
)

logger = logging.getLogger(__name__)


##############################################################
# 처리 성공 / 실패 데이터 분할 
##############################################################
def separate_success_and_fail(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """성공/실패 데이터를 `Status`와 동일한 값(`state` 컬럼)으로 분리하고 `state`는 제거."""

    c_state = CrawlingColumn.STATE.value
    df_success = df[df[c_state] == Status.SUCCESS.value]
    df_success = df_success.drop(columns=[c_state])

    df_fail = df[df[c_state] == Status.FAIL.value]
    df_fail = df_fail.drop(columns=[c_state])

    return df_success, df_fail


##############################################################
# 특수문자 제거 
##############################################################
@lru_cache(maxsize=1)
def _zw_ctrl_pattern() -> re.Pattern[str]:
    return re.compile(r"[\u200b-\u200d\ufeff]|[\x00-\x08\x0b\x0c\x0e-\x1f]")

def _clean_special_cell(v: object) -> object:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return v
    t = str(v)
    t = _zw_ctrl_pattern().sub("", t)
    return t.replace("\u00a0", " ")

def cleaning_special_characters(df: pd.DataFrame) -> pd.DataFrame:
    text_cols = (CrawlingColumn.TITLE.value, CrawlingColumn.CONTENT.value)
    cols = [c for c in text_cols if c in df.columns]
    if not cols:
        return df
    out = df.copy()
    for c in cols:
        out[c] = out[c].map(_clean_special_cell)
    return out


##############################################################
# 연속 줄바꿈 제거 
##############################################################
def _collapse_newlines_cell(v: object) -> object:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return v
    return re.sub(r"\n+", "\n", str(v))

def cleaning_continuous_newlines(df: pd.DataFrame) -> pd.DataFrame:
    text_cols = (CrawlingColumn.TITLE.value, CrawlingColumn.CONTENT.value)
    cols = [c for c in text_cols if c in df.columns]
    if not cols:
        return df
    out = df.copy()
    for c in cols:
        out[c] = out[c].map(_collapse_newlines_cell)
    return out

##############################################################
# 연속 공백 제거 
##############################################################
def _collapse_spaces_cell(v: object) -> object:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return v
    return re.sub(r"[ \t]+", " ", str(v))

def cleaning_continuous_spaces(df: pd.DataFrame) -> pd.DataFrame:
    text_cols = (CrawlingColumn.TITLE.value, CrawlingColumn.CONTENT.value)
    cols = [c for c in text_cols if c in df.columns]
    if not cols:
        return df
    out = df.copy()
    for c in cols:
        out[c] = out[c].map(_collapse_spaces_cell)
    return out




##############################################################
# 데이터 프레임을 가지고 컬럼별로 가공 
##############################################################
def cleaning_data_in_df(df: pd.DataFrame) -> pd.DataFrame:
    """ 데이터에서 각 컬럼에 대해 전처리 진행  """

    ##############################
    # 읽어온 데이터 처리 
    ##############################
    c_state = CrawlingColumn.STATE.value
    df = df.copy()
    df[c_state] = Status.SUCCESS.value
    df = df.drop_duplicates(subset=[CrawlingColumn.THREAD.value], keep="last")

    #############################################
    # 필수 컬럼에 결측치 있으면 bad -> Fail 처리
    #############################################
    required = (
        CrawlingColumn.TITLE,
        CrawlingColumn.CONTENT,
        CrawlingColumn.ARTICLE_URL,
        CrawlingColumn.CREATED_AT,
        CrawlingColumn.THREAD,
        CrawlingColumn.CATEGORY_CD,
    )
    for col in required:
        name = col.value
        if col is CrawlingColumn.CREATED_AT:
            bad = _coerce_created_at(df[name]).isna()
        else:
            bad = df[name].isna()
        df.loc[bad, c_state] = Status.FAIL.value

    #############################################
    # 특수문자, 연속 공백, 연속 줄바꿈 제거
    #############################################
    ok = df[c_state] == Status.SUCCESS.value
    if ok.any():
        try:
            part = cleaning_special_characters(df.loc[ok].copy())
            part = cleaning_continuous_spaces(part)
            part = cleaning_continuous_newlines(part)
            df.loc[ok, part.columns] = part
        except (OSError, ValueError, TypeError, re.error):
            df.loc[ok, c_state] = Status.FAIL.value

    n_ok = int((df[c_state] == Status.SUCCESS.value).sum())
    n_fail = int((df[c_state] == Status.FAIL.value).sum())
    logger.info("클리닝: 전처리 완료 success=%d fail=%d", n_ok, n_fail)

    return df


##############################################################
# 데이터 경로 조회 
##############################################################
def _crawling_raw_root(stage: Stage) -> Path:
    if PathConst.DIR:
        return Path(PathConst.DIR) / f"{PathConst.STAGE_KEY}={stage.value}"
    return (
        Path(__file__).resolve().parent.parent
        / f"{PathConst.STAGE_KEY}={stage.value}"
    )


def _coerce_created_at(series: pd.Series) -> pd.Series:
    """geeknews(소수 초)·pytorch(초만) 등 서로 다른 문자열 형식이 섞일 때 NaT 방지."""
    return pd.to_datetime(series, errors="coerce", format="mixed")


##############################################################
# 클리닝·세이브 단계 입력 CSV 수집 (process=raw / process=cleaning)
##############################################################
def _validate_success_thread_columns(df: pd.DataFrame) -> pd.DataFrame:
    """이후 클리닝·DB 단계에 필요한 `created_at` / `thread`가 없으면 빈 프레임으로 처리."""
    if (
        CrawlingColumn.CREATED_AT.value not in df.columns
        or CrawlingColumn.THREAD.value not in df.columns
    ):
        logger.warning("성공 CSV 로드: created_at/thread 컬럼 없음 — 중단")
        return pd.DataFrame()
    return df


def get_crawling_success_for_cleaning(service: Service) -> pd.DataFrame:
    """클리닝용: 크롤 산출(`process=raw`, …/status=success)에서 **한 소스** `{service}_*.csv`만 수집.

    - 크롤이 `build_csv_path(Stage.CRAWLING, …, service=…, …)` 로 쓴 경로와 동일한 트리를 읽는다.
    - 호출부에서 `Service` 열거를 돌리며 소스마다 1회 호출한 뒤 `concat` 하면 됨.
    - 행에 `_page_service`를 붙여 소스를 구분한다(`utils.collect_crawling_success_datas`).
    """
    th = get_last_success_date(service)
    # run 폴더(연/월/일) 하한: DB 워터마크·90일 lookback 중 더 늦은 (오래된) 쪽
    min_run_folder_date = min(
        pd.Timestamp(th).date(),
        date.today() - timedelta(days=CrawlingConstant.ETL_CRAWL_LOOKBACK_DAYS),
    )
    root = _crawling_raw_root(Stage.CRAWLING)
    if not root.is_dir():
        logger.warning("get_crawling_success_for_cleaning: process=raw 루트 없음 %s", root.resolve())
        return pd.DataFrame()

    thread_lst, _rows = collect_crawling_success_datas(
        root,
        [service.service],
        min_run_folder_date=min_run_folder_date,
    )
    if not thread_lst:
        logger.warning(
            "get_crawling_success_for_cleaning: 조건에 맞는 성공 CSV 없음 (service=%s)",
            service.service,
        )
        return pd.DataFrame()

    df = pd.concat(thread_lst, ignore_index=True)
    return _validate_success_thread_columns(df)


def get_cleaning_success_for_save(
    *, last_collected_at: datetime | None = None
) -> pd.DataFrame:
    """세이브용: 클리닝 산출(`process=cleaning`, …/status=success)의 **모든** `*.csv`를 읽는다.

    - 클리닝이 이미 여러 소스를 합친 **통합 파일**이므로, 소스별 인자는 없다.
    - run 폴더 하한: `last_collected_at`이 있으면 그 날짜, 없으면 DB `MAX(created_at)` 기준.
    """
    if last_collected_at is not None:
        min_run_folder_date = pd.Timestamp(last_collected_at).date()
    else:
        min_run_folder_date = pd.Timestamp(get_last_success_date()).date()

    root = _crawling_raw_root(Stage.CLEANING)
    if not root.is_dir():
        logger.warning("get_cleaning_success_for_save: process=cleaning 루트 없음 %s", root.resolve())
        return pd.DataFrame()

    thread_lst = collect_save_stage_success_datas(
        root, min_run_folder_date=min_run_folder_date
    )
    if not thread_lst:
        logger.warning("get_cleaning_success_for_save: 조건에 맞는 성공 CSV 없음 (cleaning 산출)")
        return pd.DataFrame()

    df = pd.concat(thread_lst, ignore_index=True)
    return _validate_success_thread_columns(df)

