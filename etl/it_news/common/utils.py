# 패키지 
import pandas as pd
from pathlib import Path
from datetime import datetime

# 모듈
from common.constant import PathConst, Stage, Status


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


def get_run_time() -> datetime:
    """실행 기준 시간을 생성"""
    return datetime.now()


def format_hhmmss(dt: datetime) -> str:
    """HHMMSS 형태 문자열 반환"""
    return dt.strftime("%H%M%S")