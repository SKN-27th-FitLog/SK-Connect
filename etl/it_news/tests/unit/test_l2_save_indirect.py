"""IT-L2-SAVE: save_threads 간접."""

from datetime import datetime
from unittest.mock import patch

import pandas as pd
import pytest

from common.constant import CrawlingColumn
from save.save import save_threads

_RUN_TIME = datetime(2026, 5, 20, 12, 0, 0)


def test_it_l2_save_001_empty_input_skips() -> None:
    """IT-L2-SAVE-001: 입력 0행이면 빈 튜플."""
    with patch("save.save.get_cleaning_success_for_save", return_value=pd.DataFrame()):
        ok, fail = save_threads()
    assert ok.empty and fail.empty


def test_it_l2_save_002_filters_existing_threads(minimal_crawl_row: dict) -> None:
    """IT-L2-SAVE-002: DB에 있는 thread는 제외 후 insert."""
    c = CrawlingColumn
    df_in = pd.DataFrame(
        [
            minimal_crawl_row,
            {**minimal_crawl_row, c.THREAD.value: "pytorch_99"},
        ]
    )
    df_db = pd.DataFrame({c.THREAD.value: [minimal_crawl_row[c.THREAD.value]]})
    inserted: list[pd.DataFrame] = []

    def capture_insert(df: pd.DataFrame) -> None:
        inserted.append(df.copy())

    with (
        patch("save.save.get_cleaning_success_for_save", return_value=df_in),
        patch("save.save.fetch_crawling_dataframe", return_value=df_db),
        patch("save.save.insert_crawling_batch", side_effect=capture_insert),
        patch("save.save.save_csv"),
        patch("save.save.get_run_time", return_value=_RUN_TIME),
        patch("save.save.get_last_success_date", return_value=_RUN_TIME),
    ):
        ok, fail = save_threads()

    assert len(ok) == 1
    assert inserted[0][c.THREAD.value].iloc[0] == "pytorch_99"


def test_it_l2_save_003_insert_exception_all_fail(minimal_crawl_row: dict) -> None:
    """IT-L2-SAVE-003: insert 예외 시 전체 fail."""
    c = CrawlingColumn
    df_in = pd.DataFrame([minimal_crawl_row])

    empty_threads = pd.DataFrame({c.THREAD.value: []})

    with (
        patch("save.save.get_cleaning_success_for_save", return_value=df_in),
        patch("save.save.fetch_crawling_dataframe", return_value=empty_threads),
        patch("save.save.insert_crawling_batch", side_effect=RuntimeError("db")),
        patch("save.save.save_csv"),
        patch("save.save.get_run_time", return_value=_RUN_TIME),
        patch("save.save.get_last_success_date", return_value=_RUN_TIME),
    ):
        ok, fail = save_threads()

    assert ok.empty and len(fail) == 1
