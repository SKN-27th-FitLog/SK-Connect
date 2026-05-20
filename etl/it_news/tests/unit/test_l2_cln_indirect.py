"""IT-L2-CLN: cleaning_threads 간접."""

from datetime import datetime
from unittest.mock import patch

import pandas as pd

from cleaning.cleaning import cleaning_threads


def test_it_l2_cln_001_cleaning_threads_writes_csv(minimal_crawl_row: dict) -> None:
    """IT-L2-CLN-001: raw 로드·전처리·cleaning CSV (patch)."""
    saved: list = []

    with (
        patch(
            "cleaning.cleaning.get_crawling_success_for_cleaning",
            return_value=pd.DataFrame([minimal_crawl_row]),
        ),
        patch("cleaning.cleaning.save_csv", side_effect=lambda df, p: saved.append(len(df))),
        patch(
            "cleaning.cleaning.get_run_time",
            return_value=datetime(2026, 5, 20, 12, 0, 0),
        ),
    ):
        ok, fail = cleaning_threads()

    assert len(ok) >= 1
    assert len(saved) >= 1
