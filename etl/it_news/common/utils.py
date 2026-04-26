# 패키지
import re
from collections.abc import Iterator
import pandas as pd
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Optional

from tqdm import tqdm

# 모듈
from common.constant import PathConst, Stage, Status
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


def _iter_success_csv_paths(
    path: Path,
    service_list: list[str],
    cutoff_day: date,
) -> Iterator[Path]:
    """기준일 이상인 `status=success` 폴더 아래 `*.csv` 경로를 한 번씩 yield."""
    for service in service_list:
        service_dir = path / f"{PathConst.SERVICE_KEY}={service}"
        if not service_dir.is_dir():
            continue

        for year_dir in sorted(service_dir.glob(f"{PathConst.YEAR_KEY}=*")):
            yyyy = parse_segment_int(year_dir.name, PathConst.YEAR_KEY)
            if yyyy is None:
                continue
            for month_dir in sorted(year_dir.glob(f"{PathConst.MONTH_KEY}=*")):
                mm = parse_segment_int(month_dir.name, PathConst.MONTH_KEY)
                if mm is None:
                    continue
                for day_dir in sorted(year_dir.glob(f"{PathConst.DAY_KEY}=*")):
                    dd = parse_segment_int(day_dir.name, PathConst.DAY_KEY)
                    if dd is None:
                        continue
                    if date(yyyy, mm, dd) < cutoff_day:
                        continue

                    success_dir = day_dir / f"{PathConst.STATUS_KEY}={Status.SUCCESS.value}"
                    if not success_dir.is_dir():
                        continue
                    for csv_file in sorted(success_dir.glob("*.csv")):
                        yield csv_file


def collect_crawling_success_datas(
    path: Path,
    service_list: list[str],
    cutoff_day: date,
) -> list[pd.DataFrame]:
    """스테이지 루트(`.../raw=.../`)에서 서비스·년/월/일을 순회해 `cutoff_day` 이상인 성공 CSV를 읽고 DataFrame 리스트로 반환.

    크롤링·클리닝·저장(세이브) 단계가 동일한 경로 규칙(`build_csv_path`와 대응)을 쓸 때 공통으로 재사용한다.
    """
    paths = list(_iter_success_csv_paths(path, service_list, cutoff_day))
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
    """DB에 기준이 없거나 파싱할 수 없을 때 쓰는 기본 시각: 오늘 날짜 기준 n일 전 00:00."""
    return datetime.combine(date.today() - timedelta(days=90), time.min)


def coalesce_last_created_at(last_created_at: object | None) -> datetime:
    """호출부에서 넘긴 `last_created_at`을 `datetime`으로 맞춘다. None·NaT·파싱 불가면 `default_last_collected_at`."""
    ts = pd.to_datetime(last_created_at, errors="coerce")
    if pd.notna(ts):
        return ts.to_pydatetime()
    return default_last_collected_at()


def get_last_success_date() -> datetime:
    """DB `crawling.created_at` 최댓값. `MAX`가 NULL이면 `default_last_collected_at`과 동일 기준을 사용."""
    conn = PostgreDB()
    max_rows = conn.run_query("SELECT MAX(created_at) FROM crawling")
    raw = max_rows[0][0] if max_rows else None
    if raw is None:
        return default_last_collected_at()
    return raw