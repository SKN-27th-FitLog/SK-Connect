"""IT-L3-PLN: run_pipeline 예외 전파."""

from unittest.mock import patch

import pytest

from pipeline import run_pipeline


def test_it_l3_pln_002_pipeline_propagates_stage_error() -> None:
    """IT-L3-PLN-002: 중간 단계 예외 전파."""
    with (
        patch("pipeline.get_last_success_date"),
        patch("pipeline.crawling_thread_geeknews", side_effect=RuntimeError("crawl fail")),
    ):
        with pytest.raises(RuntimeError, match="crawl fail"):
            run_pipeline()
