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
    default_last_collected_at,
    get_existing_crawling_threads,
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


def _filter_crawl_rows_for_cleaning(
    df: pd.DataFrame,
    *,
    th_geek: datetime,
    th_pt: datetime,
) -> pd.DataFrame:
    """diagram 2단계: DB 소스별 워터마크 + 미적재 thread는 90일 이내면 포함."""
    c = _coerce_created_at(df[CrawlingColumn.CREATED_AT.value])
    t_g, t_p = pd.Timestamp(th_geek), pd.Timestamp(th_pt)
    is_pt = (
        df[CrawlingColumn.THREAD.value]
        .fillna("")
        .astype(str)
        .str.startswith(f"{Service.PYTORCH.service}_")
    )
    th_series = pd.Series(t_g, index=df.index).where(~is_pt, t_p)

    d0 = pd.Timestamp(default_last_collected_at())
    thread_str = df[CrawlingColumn.THREAD.value].fillna("").astype(str)
    uids = thread_str[thread_str.str.len() > 0].unique().tolist()
    in_db = get_existing_crawling_threads(uids)
    not_in_db = ~thread_str.isin(in_db) & thread_str.str.len().gt(0)

    by_date = c > th_series
    keep = by_date | (not_in_db & (c > d0))
    return df.loc[keep].copy()


def get_success_threads(
    stage: Stage,
    service: Service,
    *,
    last_collected_at: datetime | None = None,
) -> pd.DataFrame:
    """`raw=<stage>` 아래 `service=…/…/status=success/*.csv`를 한 `Service`에 대해 읽는다.
    CRAWLING: geeknews/pytorch(호출부에서 2회 후 concat+필터). CLEANING+IT_NEWS: 클리닝 산출 로드(행 필터는 호출부)."""
    if stage is Stage.SAVE:
        raise ValueError("get_success_threads: 읽기 경로는 Stage.CLEANING(클리닝 산출)을 사용. Stage.SAVE 는 출력 단계")

    if stage is Stage.CRAWLING:
        if service not in (Service.GEEKNEWS, Service.PYTORCH):
            raise ValueError("Stage.CRAWLING 은 Service.GEEKNEWS 또는 Service.PYTORCH 만 지원")
        th = get_last_success_date(service)
        min_run_folder_date = min(
            pd.Timestamp(th).date(),
            date.today() - timedelta(days=CrawlingConstant.ETL_CRAWL_LOOKBACK_DAYS),
        )
    elif stage is Stage.CLEANING:
        if service is not Service.IT_NEWS:
            raise ValueError("Stage.CLEANING 은 Service.IT_NEWS 만 지원")
        if last_collected_at is not None:
            min_run_folder_date = pd.Timestamp(last_collected_at).date()
        else:
            min_run_folder_date = pd.Timestamp(get_last_success_date()).date()
    else:
        raise ValueError(
            f"get_success_threads: 지원하지 않는 stage {stage!r} (CLEANING, CRAWLING만)"
        )

    service_list = [service.service]
    root = _crawling_raw_root(stage)
    if not root.is_dir():
        logger.warning("get_success_threads: raw=%s 루트 없음 %s", stage.value, root.resolve())
        return pd.DataFrame()

    thread_lst, _rows = collect_crawling_success_datas(
        root,
        service_list,
        min_run_folder_date=min_run_folder_date,
    )

    if not thread_lst:
        logger.warning("get_success_threads: 조건에 맞는 성공 CSV 없음 (stage=%s, service=%s)", stage.value, service.service)
        return pd.DataFrame()

    df = pd.concat(thread_lst, ignore_index=True)

    if (
        CrawlingColumn.CREATED_AT.value not in df.columns
        or CrawlingColumn.THREAD.value not in df.columns
    ):
        logger.warning("get_success_threads: created_at/thread 컬럼 없음 — 중단")
        return pd.DataFrame()

    return df














