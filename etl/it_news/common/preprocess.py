# 패키지
import html
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
from common.errors import EtlErrors
from common.utils import (
    collect_crawling_success_datas,
    collect_save_stage_success_datas,
)
from postgresql.watermark import get_last_success_date

logger = logging.getLogger(__name__)


##############################################################
# 처리 성공 / 실패 데이터 분할 
##############################################################
def separate_success_and_fail(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """`state` 컬럼으로 success/fail DataFrame을 나누고 `state` 컬럼을 제거한다.

    Note:
        함수 유형: B — DataFrame 분할
        안전성: Level 0
        불변 규칙: `state == success|fail`만 각각 포함
    """

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
    """title·content에서 ZW·제어문자·NBSP를 정리한다.

    Note:
        함수 유형: B — 데이터 변환
        안전성: Level 0
    """
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
    """title·content의 연속 줄바꿈을 하나로 축소한다.

    Note:
        함수 유형: B — 데이터 변환
        안전성: Level 0
    """
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
    """title·content의 연속 공백·탭을 단일 공백으로 축소한다.

    Note:
        함수 유형: B — 데이터 변환
        안전성: Level 0
    """
    text_cols = (CrawlingColumn.TITLE.value, CrawlingColumn.CONTENT.value)
    cols = [c for c in text_cols if c in df.columns]
    if not cols:
        return df
    out = df.copy()
    for c in cols:
        out[c] = out[c].map(_collapse_spaces_cell)
    return out


##############################################################
# 게시글 URL → 제목 텍스트 앵커 HTML
##############################################################
def _article_url_to_anchor_cell(
    title: object,
    url: object,
    *,
    max_article_url_len: int = 500,
) -> str:
    """제목·URL을 ``<a href="원본주소">제목</a>`` 로 만든다. URL은 의미 변경 없이 ``href``용으로만 이스케이프.

    DB ``crawling.article_url`` 이 varchar(500) 이라 전체 문자열이 넘치면 표시 제목만 잘라 맞춘다.
    """
    if url is None or (isinstance(url, float) and pd.isna(url)):
        return ""
    raw_u = str(url).strip()
    if not raw_u:
        return ""

    if title is None or (isinstance(title, float) and pd.isna(title)):
        link_label = ""
    else:
        link_label = str(title).strip()

    esc_u = html.escape(raw_u, quote=True)
    prefix = '<a href="'
    mid = '">'
    suffix = "</a>"
    fixed_len = len(prefix) + len(esc_u) + len(mid) + len(suffix)
    budget = max_article_url_len - fixed_len

    if budget <= 0:
        # 주소만으로 한계 초과 시 원 문자열을 가능한 만큼만 반환
        return raw_u[:max_article_url_len]

    esc_t = html.escape(link_label, quote=True)
    if len(esc_t) <= budget:
        visible = esc_t
    elif budget <= 1:
        visible = "…"
    else:
        visible = esc_t[: budget - 1] + "…"

    return f"{prefix}{esc_u}{mid}{visible}{suffix}"


def wrap_article_url_as_html_anchor(df: pd.DataFrame) -> pd.DataFrame:
    """`article_url`을 `<a href="…">제목</a>` HTML로 치환한다(varchar 500 이내).

    Note:
        함수 유형: B — 데이터 변환
        안전성: Level 0
        불변 규칙: URL은 escape; 표시 제목만 길이 예산에 맞게 절단
    """
    url_c = CrawlingColumn.ARTICLE_URL.value
    title_c = CrawlingColumn.TITLE.value
    if url_c not in df.columns or title_c not in df.columns:
        return df

    out = df.copy()
    pairs = zip(out[title_c].tolist(), out[url_c].tolist(), strict=True)
    out[url_c] = [_article_url_to_anchor_cell(t, u) for t, u in pairs]
    return out


##############################################################
# 데이터 프레임을 가지고 컬럼별로 가공 
##############################################################
def cleaning_data_in_df(df: pd.DataFrame) -> pd.DataFrame:
    """클리닝용 DataFrame 전처리: 중복·필수값·텍스트 정규화·`state` 부여.

    Note:
        함수 유형: B+C — 변환 + 필수 컬럼 검증
        안전성: Level 0
        불변 규칙: `thread` 중복은 last 유지; 결측·전처리 예외 행은 `state=fail`
    """

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
            part = wrap_article_url_as_html_anchor(part)
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
        logger.warning(EtlErrors.Preprocess.missing_columns_on_load())
        return pd.DataFrame()
    return df


def get_crawling_success_for_cleaning(service: Service) -> pd.DataFrame:
    """클리닝 입력: 한 `Service`의 raw success CSV를 워터마크·run 하한으로 로드한다.

    Note:
        함수 유형: E+D — CSV 읽기 + DB 워터마크 조회
        안전성: Level 1
        불변 규칙: `created_at`/`thread` 없으면 빈 DataFrame; `_page_service` 태그
        부작용: 없음(DB 읽기만)
    """
    th = get_last_success_date(service)
    # run 폴더(연/월/일) 하한: DB 워터마크·90일 lookback 중 더 늦은 (오래된) 쪽
    min_run_folder_date = min(
        pd.Timestamp(th).date(),
        date.today() - timedelta(days=CrawlingConstant.ETL_CRAWL_LOOKBACK_DAYS),
    )
    root = _crawling_raw_root(Stage.CRAWLING)
    if not root.is_dir():
        logger.warning(EtlErrors.Preprocess.raw_root_missing(root.resolve()))
        return pd.DataFrame()

    thread_lst, _rows = collect_crawling_success_datas(
        root,
        [service.service],
        min_run_folder_date=min_run_folder_date,
    )
    if not thread_lst:
        logger.warning(EtlErrors.Preprocess.no_crawling_csv(service.service))
        return pd.DataFrame()

    df = pd.concat(thread_lst, ignore_index=True)
    return _validate_success_thread_columns(df)


def get_cleaning_success_for_save(
    *, last_collected_at: datetime | None = None
) -> pd.DataFrame:
    """save 입력: cleaning success CSV를 run 하한으로 모두 로드한다.

    Note:
        함수 유형: E+D — CSV 읽기 + 워터마크(선택)
        안전성: Level 1
        불변 규칙: 소스별 인자 없음(통합 파일); `created_at`/`thread` 없으면 빈 DF
    """
    if last_collected_at is not None:
        min_run_folder_date = pd.Timestamp(last_collected_at).date()
    else:
        min_run_folder_date = pd.Timestamp(get_last_success_date()).date()

    root = _crawling_raw_root(Stage.CLEANING)
    if not root.is_dir():
        logger.warning(EtlErrors.Preprocess.cleaning_root_missing(root.resolve()))
        return pd.DataFrame()

    thread_lst = collect_save_stage_success_datas(
        root, min_run_folder_date=min_run_folder_date
    )
    if not thread_lst:
        logger.warning(EtlErrors.Preprocess.no_cleaning_csv())
        return pd.DataFrame()

    df = pd.concat(thread_lst, ignore_index=True)
    return _validate_success_thread_columns(df)

