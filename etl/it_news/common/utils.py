# 패키지
import re
from collections.abc import Iterator
import pandas as pd
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Optional

# 모듈
from common.constant import CodeTable, CrawlingColumn, CrawlingConstant, PathConst, Stage, Status

###############################################################
# 데이터 파일 저장 관련 
###############################################################
def save_csv(df: pd.DataFrame, path: Path) -> Path:
    """CSV 파일 저장"""

    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding=CrawlingConstant.CSV_ENCODING)

    return path


def build_csv_path(
    stage: Stage,
    information_cd: str,
    service: str,
    status: Status,
    run_time: datetime,
) -> Path:
    """CSV 저장 경로 생성 (`PathConst.CODE_TABLE_KEY` = ``information_cd``)."""

    file_name = f"{service}_{format_hhmmss(run_time)}.csv"

    return (
        Path(PathConst.DIR)
        / f"{PathConst.STAGE_KEY}={stage.value}"
    ) / (
        f"{PathConst.CODE_TABLE_KEY}={information_cd}"
    ) / (
        f"{PathConst.YEAR_KEY}={run_time.year:04d}"
    ) / (
        f"{PathConst.MONTH_KEY}={run_time.month:02d}"
    ) / (
        f"{PathConst.DAY_KEY}={run_time.day:02d}"
    ) / (
        f"{PathConst.STATUS_KEY}={status.value}"
    ) / file_name


def information_cd_for_path(df: pd.DataFrame) -> str:
    """``crawling.information_cd``와 동일한 열에서 경로 세그먼트용 코드 문자열을 고른다.

    열이 없거나 값이 비면 ``CodeTable.INFORMATION_IT``; 여러 값이면 mode(동률이면 첫 mode).
    """
    col = CrawlingColumn.INFORMATION_CD.value
    if df.empty or col not in df.columns:
        return CodeTable.INFORMATION_IT.value
    s = df[col].dropna()
    if s.empty:
        return CodeTable.INFORMATION_IT.value
    mode = s.astype(str).mode()
    if mode.empty:
        return CodeTable.INFORMATION_IT.value
    return str(mode.iloc[0])


# 폴더 이름에서 인자를 추출하는 함수 
def parse_segment_int(dirname: str, key: str) -> int | None:
    """`year=2026` 형태 디렉터리 이름에서 정수만 추출하는 함수 ."""
    prefix = f"{key}="
    if not dirname.startswith(prefix):
        return None
    try:
        return int(dirname[len(prefix) :])
    except ValueError:
        return None


def _iter_keyed_subdirs(path: Path, key: str) -> list[Path]:
    """`{key}=*` 형식 이름의 **직접** 자식 디렉터리만 뽑는다.

    `Path.glob(f\"{key}=*\")` 는 Windows + ‘=’ 가 들어가는 상위 경로(예: `raw=crawling`)에서 빈 결과를 주는
    사례가 있어, `iterdir` + `startswith` 로 맞춘다.
    """
    if not path.is_dir():
        return []
    prefix = f"{key}="
    out: list[Path] = []
    for p in path.iterdir():
        try:
            if p.is_dir() and p.name.startswith(prefix):
                out.append(p)
        except OSError:
            continue
    return sorted(out, key=lambda x: x.name)


def _iter_success_csv_files_in_dir(success_dir: Path) -> list[Path]:
    """`status=success` 폴더 안의 `*.csv` (파일만). `glob` 대신 `iterdir` 사용."""
    if not success_dir.is_dir():
        return []
    out: list[Path] = []
    for p in success_dir.iterdir():
        try:
            if p.is_file() and p.suffix.lower() == ".csv":
                out.append(p)
        except OSError:
            continue
    return sorted(out, key=lambda x: x.name)


def _iter_code_table_success_csv_paths(
    process_root: Path,
    min_run_folder_date: date,
    *,
    filename_prefix: str | None = None,
) -> Iterator[Path]:
    """`build_csv_path`와 동일: `process=…/information_cd=…/year/…/day/…/status=success/*.csv`.

    `filename_prefix`가 있으면 `{prefix}_`로 시작하는 CSV만(크롤 `geeknews_`, `pytorch_` 등).
    `None`이면 success 폴더의 모든 `*.csv`(save 단계: 클리닝 산출 통합).
    """
    if not process_root.is_dir():
        return
    for _information_cd_dir in _iter_keyed_subdirs(process_root, PathConst.CODE_TABLE_KEY):
        for year_dir in _iter_keyed_subdirs(_information_cd_dir, PathConst.YEAR_KEY):
            yyyy = parse_segment_int(year_dir.name, PathConst.YEAR_KEY)
            if yyyy is None:
                continue
            for month_dir in _iter_keyed_subdirs(year_dir, PathConst.MONTH_KEY):
                mm = parse_segment_int(month_dir.name, PathConst.MONTH_KEY)
                if mm is None:
                    continue
                for day_dir in _iter_keyed_subdirs(month_dir, PathConst.DAY_KEY):
                    dd = parse_segment_int(day_dir.name, PathConst.DAY_KEY)
                    if dd is None:
                        continue
                    if date(yyyy, mm, dd) < min_run_folder_date:
                        continue
                    success_dir = day_dir / f"{PathConst.STATUS_KEY}={Status.SUCCESS.value}"
                    if not success_dir.is_dir():
                        continue
                    for csv_path in _iter_success_csv_files_in_dir(success_dir):
                        if filename_prefix is not None and not csv_path.name.startswith(
                            f"{filename_prefix}_"
                        ):
                            continue
                        yield csv_path


def collect_crawling_success_datas(
    process_root: Path,
    service_list: list[str],
    *,
    min_run_folder_date: date,
) -> tuple[list[pd.DataFrame], dict[str, int]]:
    """`process=raw` … `…/status=success/{service}_*.csv`를 서비스명별로 읽는다(클리닝 입력).

    각 DataFrame에 `_page_service`를 붙인다. 반환: (프레임 목록, service별 로드 직후 행 수)
    """
    rows_by_service: dict[str, int] = dict.fromkeys(service_list, 0)
    thread_lst: list[pd.DataFrame] = []
    for service in service_list:
        for csv_file in _iter_code_table_success_csv_paths(
            process_root, min_run_folder_date, filename_prefix=service
        ):
            try:
                tdf = pd.read_csv(csv_file, encoding=CrawlingConstant.CSV_ENCODING)
            except (OSError, ValueError, UnicodeDecodeError, pd.errors.EmptyDataError):
                continue
            tdf = tdf.copy()
            tdf[CrawlingColumn.PAGE_SERVICE.value] = service
            rows_by_service[service] += len(tdf)
            thread_lst.append(tdf)
    return thread_lst, rows_by_service


def collect_save_stage_success_datas(
    process_root: Path,
    *,
    min_run_folder_date: date,
) -> list[pd.DataFrame]:
    """`process=cleaning` … `…/status=success/*.csv` 전부(클리닝 이후는 파일이 통합된 상태)."""
    thread_lst: list[pd.DataFrame] = []
    for csv_file in _iter_code_table_success_csv_paths(
        process_root, min_run_folder_date, filename_prefix=None
    ):
        try:
            tdf = pd.read_csv(csv_file, encoding=CrawlingConstant.CSV_ENCODING)
        except (OSError, ValueError, UnicodeDecodeError, pd.errors.EmptyDataError):
            continue
        thread_lst.append(tdf)
    return thread_lst


###############################################################
# 시간 관련
###############################################################
def get_run_time() -> datetime:
    """실행 기준 시간을 생성"""
    return datetime.now()


def format_hhmmss(dt: datetime) -> str:
    """HHMMSS 형태 문자열 반환"""
    return dt.strftime("%H%M%S")


def korean_relative_time(text: str, now: Optional[datetime] = None) -> Optional[datetime]:
    """'8시간전', '3일전' 등 한국어 상대 시각 문자열을 now 기준으로 역산한 datetime."""
    now = now or datetime.now()
    text = text.strip()
    if not text:
        return None

    patterns = [
        (r"(\d+)\s*초전", lambda n: timedelta(seconds=int(n))),
        (r"(\d+)\s*분전", lambda n: timedelta(minutes=int(n))),
        (r"(\d+)\s*시간전", lambda n: timedelta(hours=int(n))),
        (r"(\d+)\s*일전", lambda n: timedelta(days=int(n))),
        (r"(\d+)\s*주전", lambda n: timedelta(weeks=int(n))),
        (r"(\d+)\s*개월전", lambda n: timedelta(days=int(n) * 30)),
        (r"(\d+)\s*년전", lambda n: timedelta(days=int(n) * 365)),
    ]
    for pat, delta_fn in patterns:
        m = re.match(pat, text)
        if m:
            return now - delta_fn(m.group(1))

    if text in ("방금", "방금전", "방금 전"):
        return now

    return None


##############################################
# 마지막 수집일(크롤링 기준 시각)
##############################################


def default_last_collected_at() -> datetime:
    """최초 적재( DB에 기존 row 없음 )일 때의 워터마크: 오늘 00:00 기준 `ETL_CRAWL_LOOKBACK_DAYS`일 이전 00:00.

    그 **이후**에 발행·수집된 글(행 `created_at` > 이 시각)만 후속 단계에서 “신규”로 다루기 위한 기준. 이미 `get_last_success_date`가
    `MAX(created_at)`을 줄 때는 그 값이 우선한다.
    """
    return datetime.combine(
        date.today() - timedelta(days=CrawlingConstant.ETL_CRAWL_LOOKBACK_DAYS), time.min
    )


def coalesce_last_created_at(last_created_at: object | None) -> datetime:
    """호출부에서 온 `last_created_at`을 `datetime`으로. None / NaT / 파싱 실패 → `default_last_collected_at` (최초 90일 워터마크)."""
    ts = pd.to_datetime(last_created_at, errors="coerce")
    if pd.notna(ts):
        return ts.to_pydatetime()
    return default_last_collected_at()
