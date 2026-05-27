"""PA-L3-KW: analyze_keywords 간접 검증 (extract_keywords·merge patch)."""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from analyze_keywords import analyze_keywords
from common.constant import AnalysisColumn, CodeTable


@patch("analyze_keywords.merge_analysis_data")
@patch("analyze_keywords.extract_keywords")
@patch("analyze_keywords.get_analysis_data")
def test_pa_l3_kw_001_missing_columns(
    mock_get: MagicMock,
    mock_extract: MagicMock,
    mock_merge: MagicMock,
) -> None:
    """PA-L3-KW-001 [실패]: 필수 컬럼 누락 시 ValueError, merge·extract 미호출."""
    mock_get.return_value = pd.DataFrame({AnalysisColumn.CONTENT.value: ["body"]})

    with pytest.raises(ValueError, match="keywords"):
        analyze_keywords()

    mock_merge.assert_not_called()
    mock_extract.assert_not_called()


@patch("analyze_keywords.merge_analysis_data")
@patch("analyze_keywords.extract_keywords")
@patch("analyze_keywords.get_analysis_data")
def test_pa_l3_kw_002_no_pending_rows(
    mock_get: MagicMock,
    mock_extract: MagicMock,
    mock_merge: MagicMock,
) -> None:
    """PA-L3-KW-002 [경계]: keywords가 모두 있으면 extract·merge 미호출."""
    mock_get.return_value = pd.DataFrame(
        {
            AnalysisColumn.CONTENT.value: ["body"],
            AnalysisColumn.KEYWORDS.value: ["#already#"],
            AnalysisColumn.INFORMATION_CD.value: [CodeTable.INFORMATION_RESTAURANT.value],
            AnalysisColumn.SENTIMENTAL.value: ["positive"],
        }
    )

    analyze_keywords()
    mock_merge.assert_not_called()
    mock_extract.assert_not_called()


@patch("analyze_keywords.merge_analysis_data")
@patch("analyze_keywords.extract_keywords")
@patch("analyze_keywords.BertTokenizer")
@patch("analyze_keywords.get_analysis_data")
def test_pa_l3_kw_003_excludes_ic02(
    mock_get: MagicMock,
    mock_tokenizer_cls: MagicMock,
    mock_extract: MagicMock,
    mock_merge: MagicMock,
) -> None:
    """PA-L3-KW-003 [불변]: IC02 제외·IC01 pending 1건만 extract."""
    mock_get.return_value = pd.DataFrame(
        {
            AnalysisColumn.CONTENT.value: ["a", "b"],
            AnalysisColumn.KEYWORDS.value: [pd.NA, pd.NA],
            AnalysisColumn.INFORMATION_CD.value: [
                CodeTable.INFORMATION_IT_INFO.value,
                CodeTable.INFORMATION_RESTAURANT.value,
            ],
            AnalysisColumn.SENTIMENTAL.value: ["positive", "positive"],
        }
    )
    mock_extract.return_value = "#b#"
    mock_tokenizer_cls.return_value = MagicMock()

    analyze_keywords()

    mock_merge.assert_called_once()
    df = mock_merge.call_args[0][0]
    assert len(df) == 1
    assert df[AnalysisColumn.INFORMATION_CD.value].iloc[0] == CodeTable.INFORMATION_RESTAURANT.value
    mock_extract.assert_called_once()


@patch("analyze_keywords.merge_analysis_data")
@patch("analyze_keywords.extract_keywords")
@patch("analyze_keywords.BertTokenizer")
@patch("analyze_keywords.get_analysis_data")
def test_pa_l3_kw_004_excludes_empty_content(
    mock_get: MagicMock,
    mock_tokenizer_cls: MagicMock,
    mock_extract: MagicMock,
    mock_merge: MagicMock,
) -> None:
    """PA-L3-KW-004 [불변]: 빈 content pending 행 제외."""
    mock_get.return_value = pd.DataFrame(
        {
            AnalysisColumn.CONTENT.value: ["", "맛있다"],
            AnalysisColumn.KEYWORDS.value: [pd.NA, pd.NA],
            AnalysisColumn.INFORMATION_CD.value: [
                CodeTable.INFORMATION_RESTAURANT.value,
                CodeTable.INFORMATION_RESTAURANT.value,
            ],
            AnalysisColumn.SENTIMENTAL.value: ["positive", "positive"],
        }
    )
    mock_extract.return_value = "#맛있다#"
    mock_tokenizer_cls.return_value = MagicMock()

    analyze_keywords()

    mock_merge.assert_called_once()
    df = mock_merge.call_args[0][0]
    assert len(df) == 1
    mock_extract.assert_called_once()


@patch("analyze_keywords.merge_analysis_data")
@patch("analyze_keywords.extract_keywords")
@patch("analyze_keywords.BertTokenizer")
@patch("analyze_keywords.get_analysis_data")
def test_pa_l3_kw_005_excludes_null_sentimental(
    mock_get: MagicMock,
    mock_tokenizer_cls: MagicMock,
    mock_extract: MagicMock,
    mock_merge: MagicMock,
) -> None:
    """PA-L3-KW-005 [불변]: sentimental 결측 행 제외."""
    mock_get.return_value = pd.DataFrame(
        {
            AnalysisColumn.CONTENT.value: ["a", "b"],
            AnalysisColumn.KEYWORDS.value: [pd.NA, pd.NA],
            AnalysisColumn.INFORMATION_CD.value: [
                CodeTable.INFORMATION_RESTAURANT.value,
                CodeTable.INFORMATION_RESTAURANT.value,
            ],
            AnalysisColumn.SENTIMENTAL.value: [None, "positive"],
        }
    )
    mock_extract.return_value = "#b#"
    mock_tokenizer_cls.return_value = MagicMock()

    analyze_keywords()

    mock_merge.assert_called_once()
    df = mock_merge.call_args[0][0]
    assert len(df) == 1
    mock_extract.assert_called_once()


@patch("analyze_keywords.merge_analysis_data")
@patch("analyze_keywords.extract_keywords")
@patch("analyze_keywords.BertTokenizer")
@patch("analyze_keywords.get_analysis_data")
def test_pa_l3_kw_006_merge_receives_keywords(
    mock_get: MagicMock,
    mock_tokenizer_cls: MagicMock,
    mock_extract: MagicMock,
    mock_merge: MagicMock,
) -> None:
    """PA-L3-KW-006 [정상]: extract_keywords 결과가 merge DataFrame에 반영(간접)."""
    mock_get.return_value = pd.DataFrame(
        {
            AnalysisColumn.CRAWLING_ID.value: [101],
            AnalysisColumn.CONTENT.value: ["맛있다"],
            AnalysisColumn.KEYWORDS.value: [pd.NA],
            AnalysisColumn.INFORMATION_CD.value: [CodeTable.INFORMATION_RESTAURANT.value],
            AnalysisColumn.SENTIMENTAL.value: ["positive"],
        }
    )
    mock_extract.return_value = "#맛있다#"
    mock_tokenizer_cls.return_value = MagicMock()

    analyze_keywords(max_rows=None)

    mock_merge.assert_called_once()
    df = mock_merge.call_args[0][0]
    assert df[AnalysisColumn.KEYWORDS.value].iloc[0] == "#맛있다#"
    mock_extract.assert_called_once()


@patch("analyze_keywords.merge_analysis_data")
@patch("analyze_keywords.extract_keywords")
@patch("analyze_keywords.BertTokenizer")
@patch("analyze_keywords.get_analysis_data")
def test_pa_l3_kw_007_max_rows_limits(
    mock_get: MagicMock,
    mock_tokenizer_cls: MagicMock,
    mock_extract: MagicMock,
    mock_merge: MagicMock,
) -> None:
    """PA-L3-KW-007 [경계]: max_rows 상한만큼만 extract 호출."""
    mock_get.return_value = pd.DataFrame(
        {
            AnalysisColumn.CONTENT.value: ["a", "b", "c"],
            AnalysisColumn.KEYWORDS.value: [pd.NA, pd.NA, pd.NA],
            AnalysisColumn.INFORMATION_CD.value: [CodeTable.INFORMATION_RESTAURANT.value] * 3,
            AnalysisColumn.SENTIMENTAL.value: ["positive"] * 3,
        }
    )
    mock_extract.return_value = "#x#"
    mock_tokenizer_cls.return_value = MagicMock()

    analyze_keywords(max_rows=2)

    assert mock_extract.call_count == 2
    mock_merge.assert_called_once()
    assert len(mock_merge.call_args[0][0]) == 2
