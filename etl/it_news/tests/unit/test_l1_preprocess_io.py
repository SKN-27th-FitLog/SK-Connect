"""IT-L1-PRE / IT-L1-UTIL: CSV 로드·run 폴더 하한."""

from datetime import date, datetime
from unittest.mock import patch

import pandas as pd

from common.constant import CrawlingColumn, Service
from common.preprocess import get_cleaning_success_for_save, get_crawling_success_for_cleaning
from common.utils import collect_crawling_success_datas
from tests.conftest import build_cleaning_csv_path, build_raw_csv_path, write_success_csv


def test_it_l1_pre_001_get_crawling_success_for_cleaning(
    tmp_path, minimal_crawl_row: dict, monkeypatch
) -> None:
    """IT-L1-PRE-001: raw success CSV 로드·_page_service."""
    run_date = date(2026, 5, 20)
    csv_path = build_raw_csv_path(tmp_path, service="geeknews", run_date=run_date)
    write_success_csv(csv_path, [minimal_crawl_row])

    with (
        patch("common.preprocess._crawling_raw_root", return_value=tmp_path / "process=raw"),
        patch(
            "common.preprocess.get_last_success_date",
            return_value=datetime(2026, 5, 19, 0, 0, 0),
        ),
    ):
        df = get_crawling_success_for_cleaning(Service.GEEKNEWS)

    assert len(df) == 1
    assert df[CrawlingColumn.PAGE_SERVICE.value].iloc[0] == "geeknews"


def test_it_l1_pre_002_get_cleaning_success_for_save(
    tmp_path, minimal_crawl_row: dict, monkeypatch
) -> None:
    """IT-L1-PRE-002: cleaning success CSV 통합 로드."""
    run_date = date(2026, 5, 20)
    csv_path = build_cleaning_csv_path(tmp_path, run_date=run_date)
    write_success_csv(csv_path, [minimal_crawl_row])

    with patch(
        "common.preprocess._crawling_raw_root",
        return_value=tmp_path / "process=cleaning",
    ):
        df = get_cleaning_success_for_save(
            last_collected_at=datetime(2026, 5, 19, 0, 0, 0)
        )

    assert len(df) == 1


def test_it_l1_util_001_collect_crawling_min_run_folder_date(
    tmp_path, minimal_crawl_row: dict
) -> None:
    """IT-L1-UTIL-001: min_run_folder_date 이전 run 폴더 스킵."""
    old = build_raw_csv_path(tmp_path, service="geeknews", run_date=date(2026, 1, 1))
    new = build_raw_csv_path(tmp_path, service="geeknews", run_date=date(2026, 5, 20))
    write_success_csv(old, [minimal_crawl_row])
    write_success_csv(new, [minimal_crawl_row])

    frames, counts = collect_crawling_success_datas(
        tmp_path / "process=raw",
        ["geeknews"],
        min_run_folder_date=date(2026, 5, 1),
    )
    assert sum(counts.values()) == 1
    assert len(frames) == 1
