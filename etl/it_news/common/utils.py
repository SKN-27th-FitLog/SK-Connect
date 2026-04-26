# 패키지
import re
from collections.abc import Iterator
import pandas as pd
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Optional

from tqdm import tqdm

# 모듈
from common.constant import CrawlingConstant, PathConst, Stage, Status
from common.postgresql.connection import PostgreDB

###############################################################
# 데이터 파일 저장 관련 
###############################################################
def save_csv(df: pd.DataFrame, path: Path) -> Path:
    """CSV 파일 저장"""

    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8")

    return path


def build_csv_path(
    stage: Stage,
    service: str,
    status: Status,
    run_time: datetime,
) -> Path:
    """CSV 저장 경로 생성"""

    file_name = f"{format_hhmmss(run_time)}.csv"

    return (
        Path(PathConst.DIR)
        / f"{PathConst.STAGE_KEY}={stage.value}"
    ) / (
        f"{PathConst.SERVICE_KEY}={service}"
    ) / (
        f"{PathConst.YEAR_KEY}={run_time.year:04d}"
    ) / (
        f"{PathConst.MONTH_KEY}={run_time.month:02d}"
    ) / (
        f"{PathConst.DAY_KEY}={run_time.day:02d}"
    ) / (
        f"{PathConst.STATUS_KEY}={status.value}"
    ) / file_name

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


def _iter_success_csv_paths(
    path: Path,
    service_list: list[str],
    min_run_folder_date: date,
) -> Iterator[Path]:
    """`status=success` 아래 `*.csv` 경로를 yield.

    - 경로의 `year=…/month=…/day=…`는 `build_csv_path(run_time)`에 쓰인 **크롤 실행일(로컬 날짜)** 이지, DB `created_at`과 같지 않을 수 있음.
    - **DB 기준 “이번에 처리할지”**는 호출 측에서 DataFrame `created_at`으로 거른다. 여기서는 `min_run_folder_date`보다 **오래된 run 폴더만** 잘라 스캔 범위를 제한한다.
    - 파일명(`HHmmss.csv`)은 구분에 쓰지 않으며, `*.csv` 전부 읽는다.
    """
    for service in service_list:
        service_dir = path / f"{PathConst.SERVICE_KEY}={service}"
        if not service_dir.is_dir():
            continue

        for year_dir in _iter_keyed_subdirs(service_dir, PathConst.YEAR_KEY):
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
                    for csv_file in _iter_success_csv_files_in_dir(success_dir):
                        yield csv_file


def collect_crawling_success_datas(
    path: Path,
    service_list: list[str],
    *,
    min_run_folder_date: date,
) -> list[pd.DataFrame]:
    """스테이지 루트(`.../raw=.../`)에서 성공 CSV를 읽는다.

    `min_run_folder_date`는 **run 폴더 날짜**가 이보다 이전이면 건너뛴다(과거 run 전체를 무한 스캔하지 않기 위함). 행 단위 기준은 `get_success_threads`의 `created_at` 필터.
    """
    paths = list(_iter_success_csv_paths(path, service_list, min_run_folder_date))
    thread_lst: list[pd.DataFrame] = []
    for csv_file in tqdm(paths, desc="크롤링 성공 CSV 로드", unit="파일"):
        try:
            tdf = pd.read_csv(csv_file, encoding="utf-8")
            thread_lst.append(tdf)
        except (OSError, ValueError, UnicodeDecodeError, pd.errors.EmptyDataError):
            continue
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


def get_last_success_date() -> datetime:
    """이미 DB(`crawling`)에 반영된 글 중 `created_at`이 가장 늦은 시각(마지막으로 적용한 글의 시각).

    한 건이라도 있으면 그걸 “그 이전은 이미 넣음”의 기준이 되고, 이후 ETL/클리닝은 글 `created_at` > 이 시각인 행만 취한다.
    `MAX(created_at)`이 NULL(최초)이면 `default_last_collected_at()` — 오늘로부터 90일 전 00:00(같은 상수)을 워터마크로 쓴다.
    """
    conn = PostgreDB()
    max_rows = conn.run_query("SELECT MAX(created_at) FROM crawling")
    raw = max_rows[0][0] if max_rows else None
    if raw is None:
        return default_last_collected_at()
    return raw


def get_last_success_date_by_thread_prefix(thread_prefix: str) -> datetime:
    """`crawling`에 이미 있는 글 중 `thread`가 해당 접두(소스)로 시작하는 행의 `MAX(created_at)`.

    geeknews / pytorch 는 `MAX(created_at)`를 **각각** 두어, 한 쪽만 DB에 쌓여도 다른 쪽 `created_at`이
    더 이른 글이 “이미 반영됨”으로 잘못 제외되지 않게 한다. 해당 접두의 행이 없으면
    `default_last_collected_at()`(최초 90일 워터마크)과 동일하게 동작.
    """
    # 고정 2종만: SQL에 그대로 넣을 수 있게 하드코딩(다른 prefix는 run_query·이스케이프 확장 이후)
    _queries = {
        "geeknews_": "SELECT MAX(created_at) FROM crawling WHERE thread ~ '^geeknews_'",
        "pytorch_": "SELECT MAX(created_at) FROM crawling WHERE thread ~ '^pytorch_'",
    }
    if thread_prefix not in _queries:
        raise ValueError("thread_prefix must be 'geeknews_' or 'pytorch_'")
    conn = PostgreDB()
    max_rows = conn.run_query(_queries[thread_prefix])
    raw = max_rows[0][0] if max_rows else None
    if raw is None:
        return default_last_collected_at()
    return raw


def get_existing_crawling_threads(threads: list[str] | None) -> set[str]:
    """`crawling`에 이미 있는 `thread` 집합(배치). 없으면 빈 set."""
    if not threads:
        return set()
    unique = list(dict.fromkeys(t.strip() for t in threads if t and str(t).strip()))
    if not unique:
        return set()
    conn = PostgreDB()
    rows = conn.run_query_params(
        "SELECT thread FROM crawling WHERE thread = ANY(%s)",
        (unique,),
    )
    return {r[0] for r in rows if r[0] is not None}