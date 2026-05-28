"""PA-L2/3-PLN: run_pipeline 간접 검증(4단계 함수 patch)."""

from unittest.mock import MagicMock, patch

import pytest

from pipeline import run_pipeline


@patch("pipeline.analyze_it_keywords")
@patch("pipeline.analyze_keywords")
@patch("pipeline.analyze_sentimental")
@patch("pipeline.get_reviews")
def test_pa_l2_pln_001_invalid_max_rows(
    mock_gr: MagicMock,
    mock_as: MagicMock,
    mock_kw: MagicMock,
    mock_it_kw: MagicMock,
) -> None:
    """PA-L2-PLN-001 [실패]: max_rows<=0이면 ValueError, 단계 함수 미호출."""
    with pytest.raises(ValueError, match="max_rows"):
        run_pipeline(max_rows=0)
    mock_gr.assert_not_called()
    mock_as.assert_not_called()
    mock_kw.assert_not_called()
    mock_it_kw.assert_not_called()


@patch("pipeline.analyze_it_keywords")
@patch("pipeline.analyze_keywords")
@patch("pipeline.analyze_sentimental")
@patch("pipeline.get_reviews")
def test_pa_l2_pln_002_step_order(
    mock_gr: MagicMock,
    mock_as: MagicMock,
    mock_kw: MagicMock,
    mock_it_kw: MagicMock,
) -> None:
    """PA-L2-PLN-002 [정상]: 기존 3단계 이후 IC02 키워드 단계 실행."""
    calls: list[str] = []

    mock_gr.side_effect = lambda: calls.append("gr")
    mock_as.side_effect = lambda: calls.append("as")
    mock_kw.side_effect = lambda max_rows=None: calls.append(f"kw:{max_rows}")
    mock_it_kw.side_effect = lambda max_rows=None, overwrite=False: calls.append(
        f"it_kw:{max_rows}:{overwrite}"
    )

    run_pipeline(max_rows=None)
    assert calls == ["gr", "as", "kw:None", "it_kw:None:False"]


@patch("pipeline.analyze_it_keywords")
@patch("pipeline.analyze_keywords")
@patch("pipeline.analyze_sentimental")
@patch("pipeline.get_reviews")
def test_pa_l2_pln_003_passes_max_rows_to_keywords(
    mock_gr: MagicMock,
    mock_as: MagicMock,
    mock_kw: MagicMock,
    mock_it_kw: MagicMock,
) -> None:
    """PA-L2-PLN-003 [정상]: max_rows는 기존 IC01 키워드에만 전달."""
    run_pipeline(max_rows=3)
    mock_kw.assert_called_once_with(max_rows=3)
    mock_it_kw.assert_called_once_with(max_rows=None, overwrite=False)


@patch("pipeline.analyze_it_keywords")
@patch("pipeline.analyze_keywords")
@patch("pipeline.analyze_sentimental")
@patch("pipeline.get_reviews")
def test_pa_l2_pln_004_passes_it_keyword_options(
    mock_gr: MagicMock,
    mock_as: MagicMock,
    mock_kw: MagicMock,
    mock_it_kw: MagicMock,
) -> None:
    """PA-L2-PLN-004 [정상]: IC02 키워드 옵션은 IC02 단계에만 전달."""
    run_pipeline(max_rows=2, it_keywords_max_rows=5, overwrite_it_keywords=True)
    mock_kw.assert_called_once_with(max_rows=2)
    mock_it_kw.assert_called_once_with(max_rows=5, overwrite=True)


@patch("pipeline.analyze_it_keywords")
@patch("pipeline.analyze_keywords")
@patch("pipeline.analyze_sentimental")
@patch("pipeline.get_reviews")
def test_pa_l2_pln_005_invalid_it_keywords_max_rows(
    mock_gr: MagicMock,
    mock_as: MagicMock,
    mock_kw: MagicMock,
    mock_it_kw: MagicMock,
) -> None:
    """PA-L2-PLN-005 [실패]: it_keywords_max_rows<=0이면 단계 함수 미호출."""
    with pytest.raises(ValueError, match="max_rows"):
        run_pipeline(it_keywords_max_rows=0)
    mock_gr.assert_not_called()
    mock_as.assert_not_called()
    mock_kw.assert_not_called()
    mock_it_kw.assert_not_called()
