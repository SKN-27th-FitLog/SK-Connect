"""PA-L2/3-PLN: run_pipeline 간접 검증."""

from unittest.mock import MagicMock, patch

import pytest

from pipeline import run_pipeline


@patch("pipeline.analyze_keywords_by_llm")
@patch("pipeline.analyze_sentimental")
@patch("pipeline.get_reviews")
def test_pa_l2_pln_001_invalid_max_rows(
    mock_gr: MagicMock,
    mock_as: MagicMock,
    mock_llm: MagicMock,
) -> None:
    with pytest.raises(ValueError, match="max_rows"):
        run_pipeline(max_rows=0)
    mock_gr.assert_not_called()
    mock_as.assert_not_called()
    mock_llm.assert_not_called()


@patch("pipeline.analyze_keywords_by_llm")
@patch("pipeline.analyze_sentimental")
@patch("pipeline.get_reviews")
def test_pa_l2_pln_002_step_order(
    mock_gr: MagicMock,
    mock_as: MagicMock,
    mock_llm: MagicMock,
) -> None:
    calls: list[str] = []

    mock_gr.side_effect = lambda: calls.append("gr")
    mock_as.side_effect = lambda: calls.append("as")
    mock_llm.side_effect = lambda max_rows=None: calls.append(f"llm:{max_rows}")

    run_pipeline(max_rows=None)
    assert calls == ["gr", "as", "llm:None"]


@patch("pipeline.analyze_keywords_by_llm")
@patch("pipeline.analyze_sentimental")
@patch("pipeline.get_reviews")
def test_pa_l2_pln_003_passes_max_rows_to_llm(
    mock_gr: MagicMock,
    mock_as: MagicMock,
    mock_llm: MagicMock,
) -> None:
    run_pipeline(max_rows=3)
    mock_llm.assert_called_once_with(max_rows=3)
