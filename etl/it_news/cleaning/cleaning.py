import logging
import re
from functools import lru_cache

import pandas as pd
from datetime import date, datetime, timedelta
from pathlib import Path

from common.constant import CrawlingConstant, PathConst, Stage, Status, PageURL
from common.utils import (
    build_csv_path,
    collect_crawling_success_datas,
    default_last_collected_at,
    get_existing_crawling_threads,
    get_last_success_date_by_thread_prefix,
    get_run_time,
    save_csv,
)

logger = logging.getLogger(__name__)


def _crawling_raw_root() -> Path:
    if PathConst.DIR:
        return Path(PathConst.DIR) / f"{PathConst.STAGE_KEY}={Stage.CRAWLING.value}"
    return (
        Path(__file__).resolve().parent.parent
        / f"{PathConst.STAGE_KEY}={Stage.CRAWLING.value}"
    )


def _date_only(d: datetime | object) -> date:
    if isinstance(d, datetime):
        return d.date()
    return pd.Timestamp(d).date()


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
    c = _coerce_created_at(df["created_at"])
    t_g, t_p = pd.Timestamp(th_geek), pd.Timestamp(th_pt)
    is_pt = df["thread"].fillna("").astype(str).str.startswith("pytorch_")
    th_series = pd.Series(t_g, index=df.index).where(~is_pt, t_p)

    d0 = pd.Timestamp(default_last_collected_at())
    thread_str = df["thread"].fillna("").astype(str)
    uids = thread_str[thread_str.str.len() > 0].unique().tolist()
    in_db = get_existing_crawling_threads(uids)
    not_in_db = ~thread_str.isin(in_db) & thread_str.str.len().gt(0)

    by_date = c > th_series
    keep = by_date | (not_in_db & (c > d0))
    return df.loc[keep].copy()


def get_success_threads() -> pd.DataFrame:
    """`PageURL`의 모든 `service`에 대응하는 `raw=crawling/service=…/…/status=success/*.csv`를 읽고,
    DB 워터마크·thread 적재 여부로 행을 거른 뒤 하나의 DataFrame으로 만든다."""
    service_list = [p.service for p in PageURL]

    th_geek = get_last_success_date_by_thread_prefix("geeknews_")
    th_pt = get_last_success_date_by_thread_prefix("pytorch_")
    min_run_folder_date = min(
        _date_only(th_geek),
        _date_only(th_pt),
        date.today() - timedelta(days=CrawlingConstant.ETL_CRAWL_LOOKBACK_DAYS),
    )

    root = _crawling_raw_root()
    if not root.is_dir():
        logger.warning("클리닝: raw=crawling 루트 없음 %s", root.resolve())
        return pd.DataFrame()

    thread_lst, rows_by_service = collect_crawling_success_datas(
        root,
        service_list,
        min_run_folder_date=min_run_folder_date,
    )

    if not thread_lst:
        logger.warning("클리닝: 조건에 맞는 크롤 성공 CSV 없음")
        return pd.DataFrame()

    df = pd.concat(thread_lst, ignore_index=True)

    if "created_at" not in df.columns or "thread" not in df.columns:
        logger.warning("클리닝: created_at/thread 컬럼 없음 — 중단")
        return pd.DataFrame()

    df = _filter_crawl_rows_for_cleaning(df, th_geek=th_geek, th_pt=th_pt)

    load_summary = ", ".join(f"{s}={rows_by_service.get(s, 0)}" for s in service_list)
    if "_page_service" in df.columns:
        after_summary = ", ".join(
            f"{s}={int((df['_page_service'] == s).sum())}" for s in service_list
        )
        df = df.drop(columns=["_page_service"])
    else:
        after_summary = "(service별 없음)"

    logger.info(
        "get_success_threads: 워터마크 geek=%s pt=%s run하한=%s | 필터 전 {%s} → 필터 후 총 %d행 {%s}",
        th_geek,
        th_pt,
        min_run_folder_date,
        load_summary,
        len(df),
        after_summary,
    )
    return df


def cleaning_data_in_df(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["state"] = "success"
    df = df.drop_duplicates(subset=["thread"], keep="last")

    required = ("title", "content", "article_url", "created_at", "thread", "category_cd")
    missing = [c for c in required if c not in df.columns]
    if missing:
        df["state"] = "fail"
    else:
        bad = pd.Series(False, index=df.index)
        for col in required:
            if col == "created_at":
                bad = bad | _coerce_created_at(df[col]).isna()
            else:
                bad = bad | df[col].isna()
        df.loc[bad, "state"] = "fail"

    ok = df["state"] == "success"
    if ok.any():
        try:
            part = cleaning_special_characters(df.loc[ok].copy())
            part = cleaning_continuous_spaces(part)
            part = cleaning_continuous_newlines(part)
            df.loc[ok, part.columns] = part
        except (OSError, ValueError, TypeError, re.error):
            df.loc[ok, "state"] = "fail"

    n_ok = int((df["state"] == "success").sum())
    n_fail = int((df["state"] == "fail").sum())
    logger.info("클리닝: 전처리 완료 success=%d fail=%d", n_ok, n_fail)
    return df


@lru_cache(maxsize=1)
def _zw_ctrl_pattern() -> re.Pattern[str]:
    return re.compile(r"[\u200b-\u200d\ufeff]|[\x00-\x08\x0b\x0c\x0e-\x1f]")


def _clean_special_cell(v: object) -> object:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return v
    t = str(v)
    t = _zw_ctrl_pattern().sub("", t)
    return t.replace("\u00a0", " ")


def _collapse_spaces_cell(v: object) -> object:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return v
    return re.sub(r"[ \t]+", " ", str(v))


def _collapse_newlines_cell(v: object) -> object:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return v
    return re.sub(r"\n+", "\n", str(v))


def cleaning_special_characters(df: pd.DataFrame) -> pd.DataFrame:
    text_cols = ("title", "content")
    cols = [c for c in text_cols if c in df.columns]
    if not cols:
        return df
    out = df.copy()
    for c in cols:
        out[c] = out[c].map(_clean_special_cell)
    return out


def cleaning_continuous_spaces(df: pd.DataFrame) -> pd.DataFrame:
    text_cols = ("title", "content")
    cols = [c for c in text_cols if c in df.columns]
    if not cols:
        return df
    out = df.copy()
    for c in cols:
        out[c] = out[c].map(_collapse_spaces_cell)
    return out


def cleaning_continuous_newlines(df: pd.DataFrame) -> pd.DataFrame:
    text_cols = ("title", "content")
    cols = [c for c in text_cols if c in df.columns]
    if not cols:
        return df
    out = df.copy()
    for c in cols:
        out[c] = out[c].map(_collapse_newlines_cell)
    return out


def separate_success_and_fail(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """ 성공 실패 데이터를 State에 따라 분리하고 실제 데이터가 아닌 State 컬럼은 제거 """

    # 성공 데이터 
    df_success = df[df["state"] == "success"]
    df_success = df_success.drop(columns=["state"])
    
    # 실패 데이터 
    df_fail = df[df["state"] == "fail"]
    df_fail = df_fail.drop(columns=["state"])

    return df_success, df_fail


def cleaning_threads(
    *,
    cleaning_service: str = "it_news",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """diagram 2단계: 성공 CSV 로드·필터 → 전처리 → success/fail CSV."""
    run_time = get_run_time()

    df = get_success_threads()
    if df.empty:
        logger.info("클리닝: 저장 생략(입력 0행)")
        return pd.DataFrame(), pd.DataFrame()

    df = cleaning_data_in_df(df)
    df_success, df_fail = separate_success_and_fail(df)

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
