"""IT-L2-UTIL: save_csv tmp_path."""

from datetime import datetime

import pandas as pd

from common.constant import CodeTable, Service, Stage, Status
from common.utils import build_csv_path, save_csv


def test_it_l2_util_001_save_csv_writes_file(tmp_path) -> None:
    """IT-L2-UTIL-001: save_csv가 파일을 생성한다."""
    path = build_csv_path(
        Stage.CRAWLING,
        CodeTable.INFORMATION_IT.value,
        Service.GEEKNEWS.service,
        Status.SUCCESS,
        datetime(2026, 5, 20, 12, 0, 0),
    )
    full = tmp_path / path
    df = pd.DataFrame({"a": [1]})
    save_csv(df, full)
    assert full.is_file()
    assert "a" in full.read_text(encoding="utf-8")
