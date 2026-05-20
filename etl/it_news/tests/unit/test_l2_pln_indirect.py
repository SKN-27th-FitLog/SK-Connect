"""IT-L2-PLN: run_pipeline 간접."""

from unittest.mock import MagicMock, patch

import pandas as pd

from pipeline import run_pipeline


def test_it_l2_pln_001_pipeline_call_order() -> None:
    """IT-L2-PLN-001: geeknews→pytorch→cleaning→save 순서."""
    calls: list[str] = []

    empty = (pd.DataFrame(), pd.DataFrame())

    def _geek(**_) -> tuple[pd.DataFrame, pd.DataFrame]:
        calls.append("geeknews")
        return empty

    def _pt(**_) -> tuple[pd.DataFrame, pd.DataFrame]:
        calls.append("pytorch")
        return empty

    def _clean() -> tuple[pd.DataFrame, pd.DataFrame]:
        calls.append("cleaning")
        return empty

    def _save() -> tuple[pd.DataFrame, pd.DataFrame]:
        calls.append("save")
        return empty

    with (
        patch("pipeline.get_last_success_date", return_value=MagicMock()),
        patch("pipeline.crawling_thread_geeknews", side_effect=_geek),
        patch("pipeline.crawling_thread_pytorch", side_effect=_pt),
        patch("pipeline.cleaning_threads", side_effect=_clean),
        patch("pipeline.save_threads", side_effect=_save),
    ):
        run_pipeline()

    assert calls == ["geeknews", "pytorch", "cleaning", "save"]
