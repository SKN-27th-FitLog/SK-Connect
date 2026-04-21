from datetime import datetime
from pathlib import Path

from common.constant import PathConst, Stage, Status
from common.utils_time import format_hhmmss


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
