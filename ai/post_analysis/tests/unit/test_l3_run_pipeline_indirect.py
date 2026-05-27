"""PA-L2/3-PLN: run_pipeline 간접 검증 (3단계 함수 patch)."""

from unittest.mock import MagicMock, patch

import pytest

from pipeline import run_pipeline


@patch("pipeline.analyze_keywords")
@patch("pipeline.analyze_sentimental")
@patch("pipeline.get_reviews")
def test_pa_l2_pln_001_invalid_max_rows(
    mock_gr: MagicMock,
    mock_as: MagicMock,
    mock_kw: MagicMock,
) -> None:
    """PA-L2-PLN-001 [실패]: max_rows<=0 이면 ValueError, 단계 함수 미호출."""
    with pytest.raises(ValueError, match="max_rows"):
        run_pipeline(max_rows=0)
    mock_gr.assert_not_called()
    mock_as.assert_not_called()
    mock_kw.assert_not_called()


@patch("pipeline.analyze_keywords")
@patch("pipeline.analyze_sentimental")
@patch("pipeline.get_reviews")
def test_pa_l2_pln_002_step_order(
    mock_gr: MagicMock,
    mock_as: MagicMock,
    mock_kw: MagicMock,
) -> None:
    """PA-L2-PLN-002 [정상]: get_reviews → analyze_sentimental → analyze_keywords 순서."""
    calls: list[str] = []

    mock_gr.side_effect = lambda: calls.append("gr")
    mock_as.side_effect = lambda: calls.append("as")
    mock_kw.side_effect = lambda max_rows=None: calls.append(f"kw:{max_rows}")

    run_pipeline(max_rows=None)
    assert calls == ["gr", "as", "kw:None"]


@patch("pipeline.analyze_keywords")
@patch("pipeline.analyze_sentimental")
@patch("pipeline.get_reviews")
def test_pa_l2_pln_003_passes_max_rows_to_keywords(
    mock_gr: MagicMock,
    mock_as: MagicMock,
    mock_kw: MagicMock,
) -> None:
    """PA-L2-PLN-003 [정상]: max_rows가 analyze_keywords에 전달."""
    run_pipeline(max_rows=3)
    mock_kw.assert_called_once_with(max_rows=3)
