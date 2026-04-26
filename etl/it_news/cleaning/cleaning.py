"""
"""

# 패키지
import logging
import re
from functools import lru_cache
import pandas as pd
from datetime import date, datetime
from pathlib import Path
from tqdm import tqdm

# 모듈
from common.constant import PathConst, Stage, Status, PageURL
from common.utils import (
    build_csv_path,
    coalesce_last_created_at,
    collect_crawling_success_datas,
    get_last_success_date,
    get_run_time,
    save_csv,
)

logger = logging.getLogger(__name__)


#################################################################
# 기준일자 이후 수집된 크롤링 성공 데이터를 모으는 함수
#################################################################
def get_success_threads(last_created_at: object | None) -> pd.DataFrame:
    """기준일 이후 크롤링 성공 CSV(`raw=crawling/.../status=success/`)를 모아 하나의 DataFrame으로 반환."""
    threshold = coalesce_last_created_at(last_created_at)
    # 구해온 시간 데이터를 가지고 비교할 날짜 데이터를 만듬
    cutoff_day = date(threshold.year, threshold.month, threshold.day)

    # build_csv_path와 동일: raw=crawling / service=... / year= / month= / day= / status=success
    crawling_root = Path(PathConst.DIR) / f"{PathConst.STAGE_KEY}={Stage.CRAWLING.value}"
    service_list = [p.service for p in PageURL]
    thread_lst = collect_crawling_success_datas(
        crawling_root, service_list, cutoff_day
    )

    if not thread_lst:
        return pd.DataFrame()

    # 게시글 리스트를 하나의 데이터 프레임으로 변환
    df = pd.concat(thread_lst, ignore_index=True)
    if "created_at" in df.columns:
        c = pd.to_datetime(df["created_at"], errors="coerce")
        df = df[c > pd.Timestamp(threshold)].copy()

    return df

##############################################
# 하나로 모아진 데이터 전처리 진행
##############################################
def cleaning_data_in_df(df: pd.DataFrame) -> pd.DataFrame:
    """하나로 모아진 데이터 전처리 진행"""
    df = df.copy()
    # state 컬럼 추가 (데이터 작업 상태 관리 , success or fail)
    df['state'] = 'success' # 기본값은 success

    # 입력된 데이터에서 thread 컬럼 기준으로 중복 체크 (UniqueID 체크 )
    # drop_duplicates에서 last 사용하는 것으로 데이터 처리 
    df = df.drop_duplicates(subset=['thread'], keep='last')

    # 이상치 체크(crawling_id 제외 — 주요 컬럼이 비어 있거나 created_at이 파싱 불가면 state = fail, 행은 유지)
    required = ("title", "content", "article_url", "created_at", "thread", "category_cd")
    missing = [c for c in required if c not in df.columns]
    if missing:
        df["state"] = "fail"
    else:
        bad = pd.Series(False, index=df.index)
        for col in tqdm(required, desc="필수 컬럼 이상치 검사", leave=False):
            if col == "created_at":
                bad = bad | pd.to_datetime(df[col], errors="coerce").isna()
            else:
                bad = bad | df[col].isna()
        df.loc[bad, "state"] = "fail"

    # 이상치 통과 행에만 정규화 (diagram: 나머지 컬럼). 예외 시 정규화 대상 전체를 fail
    ok = df["state"] == "success"
    if ok.any():
        try:
            part = cleaning_special_characters(df.loc[ok].copy())
            part = cleaning_continuous_spaces(part)
            part = cleaning_continuous_newlines(part)
            df.loc[ok, part.columns] = part
        except (OSError, ValueError, TypeError, re.error):
            df.loc[ok, "state"] = "fail"

    return df


##############################################
# 전처리 함수 (필요한 컬럼별로 실행)
##############################################

@lru_cache(maxsize=1)
def _zw_ctrl_pattern() -> re.Pattern[str]:
    """제로폭·BOM·C0 제어 문자 제거용 정규식. compile은 첫 호출 1회만 수행."""
    return re.compile(r"[\u200b-\u200d\ufeff]|[\x00-\x08\x0b\x0c\x0e-\x1f]")


def _clean_special_cell(v: object) -> object:
    """셀 하나: 스크랩 시 섞인 제로폭·제어문자·NBSP 제거."""
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return v
    t = str(v)
    t = _zw_ctrl_pattern().sub("", t)  # U+200B~D, BOM, C0 제어 등
    t = t.replace("\u00a0", " ")  # 일반 공백으로 통일
    return t


def _collapse_spaces_cell(v: object) -> object:
    """셀 하나: 스페이스·탭 연속 구간을 공백 한 칸으로."""
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return v
    return re.sub(r"[ \t]+", " ", str(v))


def _collapse_newlines_cell(v: object) -> object:
    """셀 하나: 연속 개행을 단일 \\n으로 (빈 줄 다단 합침)."""
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return v
    return re.sub(r"\n+", "\n", str(v))


def cleaning_special_characters(df: pd.DataFrame) -> pd.DataFrame:
    """제목/본문에서 제로폭·제어문자·NBSP 정리."""
    text_cols = ("title", "content")
    cols = [c for c in text_cols if c in df.columns]
    if not cols:
        return df
    out = df.copy()
    for c in tqdm(cols, desc="제로폭·제어 문자 정리 (제목/본문)", unit="col", leave=False):
        out[c] = out[c].map(_clean_special_cell)
    return out


def cleaning_continuous_spaces(df: pd.DataFrame) -> pd.DataFrame:
    """제목/본문에서 연속 스페이스·탭을 한 칸으로."""
    text_cols = ("title", "content")
    cols = [c for c in text_cols if c in df.columns]
    if not cols:
        return df
    out = df.copy()
    for c in tqdm(cols, desc="연속 공백 정리 (제목/본문)", unit="col", leave=False):
        out[c] = out[c].map(_collapse_spaces_cell)
    return out


def cleaning_continuous_newlines(df: pd.DataFrame) -> pd.DataFrame:
    """제목/본문에서 연속 줄바꿈을 한 번으로(빈 줄 난립 완화)."""
    text_cols = ("title", "content")
    cols = [c for c in text_cols if c in df.columns]
    if not cols:
        return df
    out = df.copy()
    for c in tqdm(cols, desc="연속 개행 정리 (제목/본문)", unit="col", leave=False):
        out[c] = out[c].map(_collapse_newlines_cell)
    return out


##############################################
# 전체 dataFrame 중에서 State 기준으로 성공 / 실패 데이터 분리 
##############################################
def separate_success_and_fail(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """전체 dataFrame 중에서 State 기준으로 성공 / 실패 데이터 분리"""
    df_success = df[df['state'] == 'success']
    df_fail = df[df['state'] == 'fail']

    # 분리된 데이터에서 state 컬럼 제거 
    df_success = df_success.drop(columns=['state'])
    df_fail = df_fail.drop(columns=['state'])

    return df_success, df_fail

##############################################
# 클리닝 함수 실행
# diagram: DB last 수집일 → 기준일 이후 크롤링 성공 CSV concat → 전처리 → state 분리 → CSV(opt)
##############################################
def cleaning_threads(
    last_created_at: datetime | None,
    *,
    cleaning_service: str = "it",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """게시글 목록 클리닝. `cleaning_service`는 서비스별이 아닌 병합 배치의 경로 세그먼트(`pipeline.py`의 `it`와 동일)."""
    run_time = get_run_time()
    df = get_success_threads(last_created_at)
    if df.empty:
        return pd.DataFrame(), pd.DataFrame()

    df = cleaning_data_in_df(df)
    df_success, df_fail = separate_success_and_fail(df)

    if not df_success.empty:
        path_success = build_csv_path(
            Stage.CLEANING, cleaning_service, Status.SUCCESS, run_time
        )
        save_csv(df_success, path_success)

    if not df_fail.empty:
        path_fail = build_csv_path(Stage.CLEANING, cleaning_service, Status.FAIL, run_time)
        save_csv(df_fail, path_fail)

    return df_success, df_fail


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    last_success_date = get_last_success_date()
    df_success, df_fail = cleaning_threads(last_success_date)
    logger.info(
        "cleaning done: success=%s rows, fail=%s rows",
        len(df_success),
        len(df_fail),
    )


