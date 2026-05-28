"""PA-L3-ITKW: analyze_it_keywords indirect tests for IC02 orchestration."""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from analyze_it_keywords import ItKeywordResult, analyze_it_keywords, extract_it_keywords
from common.constant import AnalysisColumn, CodeTable, CrawlingColumn


def _analysis_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            AnalysisColumn.CRAWLING_ID.value: [101, 102, 103, 104],
            AnalysisColumn.TITLE.value: ["IT A", "Meal B", "IT C", ""],
            AnalysisColumn.CONTENT.value: ["PyTorch update", "meal review", "GPU news", ""],
            AnalysisColumn.KEYWORDS.value: [pd.NA, pd.NA, "#existing", pd.NA],
            AnalysisColumn.INFORMATION_CD.value: [
                CodeTable.INFORMATION_IT_INFO.value,
                CodeTable.INFORMATION_RESTAURANT.value,
                CodeTable.INFORMATION_IT_INFO.value,
                CodeTable.INFORMATION_IT_INFO.value,
            ],
        }
    )


def _crawling_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            CrawlingColumn.CRAWLING_ID.value: [101, 103, 104],
            CrawlingColumn.VIEW_COUNT.value: [1200, 10, 999],
            CrawlingColumn.COMMENT_COUNT.value: [8, 0, 1],
            CrawlingColumn.POINT.value: [3, 0, 1],
        }
    )


@patch("analyze_it_keywords.merge_analysis_data")
@patch("analyze_it_keywords.extract_it_keywords")
@patch("analyze_it_keywords.get_crawling_data")
@patch("analyze_it_keywords.get_analysis_data")
def test_pa_l3_itkw_001_processes_ic02_missing_keywords_only(
    mock_get_analysis: MagicMock,
    mock_get_crawling: MagicMock,
    mock_extract: MagicMock,
    mock_merge: MagicMock,
) -> None:
    """기본 실행은 IC02 중 keywords 결측이고 본문 또는 제목이 있는 row만 처리한다."""
    mock_get_analysis.return_value = _analysis_df()
    mock_get_crawling.return_value = _crawling_df()
    mock_extract.return_value = ItKeywordResult(
        summary="summary",
        flow="release -> impact",
        interest_label="high",
        keywords=["PyTorch", "inference speed", "community interest"],
    )

    analyze_it_keywords()

    mock_extract.assert_called_once()
    mock_merge.assert_called_once()
    df = mock_merge.call_args[0][0]
    assert len(df) == 1
    assert list(df.columns) == [
        AnalysisColumn.CRAWLING_ID.value,
        AnalysisColumn.KEYWORDS.value,
    ]
    assert df[AnalysisColumn.CRAWLING_ID.value].iloc[0] == 101
    assert (
        df[AnalysisColumn.KEYWORDS.value].iloc[0]
        == "#PyTorch#inference speed#community interest"
    )


@patch("analyze_it_keywords.merge_analysis_data")
@patch("analyze_it_keywords.extract_it_keywords")
@patch("analyze_it_keywords.get_crawling_data")
@patch("analyze_it_keywords.get_analysis_data")
def test_pa_l3_itkw_002_overwrite_reprocesses_existing_ic02(
    mock_get_analysis: MagicMock,
    mock_get_crawling: MagicMock,
    mock_extract: MagicMock,
    mock_merge: MagicMock,
) -> None:
    """overwrite=True이면 기존 IC02 keywords row도 재처리한다."""
    mock_get_analysis.return_value = _analysis_df()
    mock_get_crawling.return_value = _crawling_df()
    mock_extract.return_value = ItKeywordResult(
        summary="summary",
        flow="release -> impact",
        interest_label="medium",
        keywords=["GPU", "developer impact"],
    )

    analyze_it_keywords(overwrite=True)

    assert mock_extract.call_count == 2
    mock_merge.assert_called_once()
    assert list(mock_merge.call_args[0][0][AnalysisColumn.CRAWLING_ID.value]) == [101, 103]


@patch("analyze_it_keywords.merge_analysis_data")
@patch("analyze_it_keywords.extract_it_keywords")
@patch("analyze_it_keywords.get_crawling_data")
@patch("analyze_it_keywords.get_analysis_data")
def test_pa_l3_itkw_003_max_rows_limits_after_filter(
    mock_get_analysis: MagicMock,
    mock_get_crawling: MagicMock,
    mock_extract: MagicMock,
    mock_merge: MagicMock,
) -> None:
    """max_rows는 IC02 필터 이후 적용한다."""
    mock_get_analysis.return_value = pd.DataFrame(
        {
            AnalysisColumn.CRAWLING_ID.value: [1, 2, 3],
            AnalysisColumn.TITLE.value: ["A", "B", "C"],
            AnalysisColumn.CONTENT.value: ["a", "b", "c"],
            AnalysisColumn.KEYWORDS.value: [pd.NA, pd.NA, pd.NA],
            AnalysisColumn.INFORMATION_CD.value: [CodeTable.INFORMATION_IT_INFO.value] * 3,
        }
    )
    mock_get_crawling.return_value = pd.DataFrame()
    mock_extract.return_value = ItKeywordResult(keywords=["keyword"])

    analyze_it_keywords(max_rows=2)

    assert mock_extract.call_count == 2
    assert len(mock_merge.call_args[0][0]) == 2


@patch("analyze_it_keywords.merge_analysis_data")
@patch("analyze_it_keywords.extract_it_keywords")
@patch("analyze_it_keywords.get_crawling_data")
@patch("analyze_it_keywords.get_analysis_data")
def test_pa_l3_itkw_004_row_failure_merges_successes_only(
    mock_get_analysis: MagicMock,
    mock_get_crawling: MagicMock,
    mock_extract: MagicMock,
    mock_merge: MagicMock,
) -> None:
    """row 단위 실패는 계속 진행하고 성공분만 MERGE한다."""
    mock_get_analysis.return_value = pd.DataFrame(
        {
            AnalysisColumn.CRAWLING_ID.value: [1, 2],
            AnalysisColumn.TITLE.value: ["A", "B"],
            AnalysisColumn.CONTENT.value: ["a", "b"],
            AnalysisColumn.KEYWORDS.value: [pd.NA, pd.NA],
            AnalysisColumn.INFORMATION_CD.value: [CodeTable.INFORMATION_IT_INFO.value] * 2,
        }
    )
    mock_get_crawling.return_value = pd.DataFrame()
    mock_extract.side_effect = [RuntimeError("ollama down"), ItKeywordResult(keywords=["success"])]

    analyze_it_keywords()

    mock_merge.assert_called_once()
    df = mock_merge.call_args[0][0]
    assert list(df[AnalysisColumn.CRAWLING_ID.value]) == [2]
    assert df[AnalysisColumn.KEYWORDS.value].iloc[0] == "#success"


@patch("analyze_it_keywords.merge_analysis_data")
@patch("analyze_it_keywords.extract_it_keywords")
@patch("analyze_it_keywords.get_crawling_data")
@patch("analyze_it_keywords.get_analysis_data")
def test_pa_l3_itkw_005_no_success_skips_merge(
    mock_get_analysis: MagicMock,
    mock_get_crawling: MagicMock,
    mock_extract: MagicMock,
    mock_merge: MagicMock,
) -> None:
    """추출 결과가 모두 비어 있으면 MERGE하지 않는다."""
    mock_get_analysis.return_value = pd.DataFrame(
        {
            AnalysisColumn.CRAWLING_ID.value: [1],
            AnalysisColumn.TITLE.value: ["A"],
            AnalysisColumn.CONTENT.value: ["a"],
            AnalysisColumn.KEYWORDS.value: [pd.NA],
            AnalysisColumn.INFORMATION_CD.value: [CodeTable.INFORMATION_IT_INFO.value],
        }
    )
    mock_get_crawling.return_value = pd.DataFrame()
    mock_extract.return_value = ItKeywordResult(keywords=[])

    analyze_it_keywords()

    mock_merge.assert_not_called()


@patch("analyze_it_keywords.merge_analysis_data")
@patch("analyze_it_keywords.extract_it_keywords")
@patch("analyze_it_keywords.get_analysis_data")
def test_pa_l3_itkw_006_missing_columns(
    mock_get_analysis: MagicMock,
    mock_extract: MagicMock,
    mock_merge: MagicMock,
) -> None:
    """필수 column이 없으면 ValueError를 발생시키고 외부 호출은 하지 않는다."""
    mock_get_analysis.return_value = pd.DataFrame({AnalysisColumn.TITLE.value: ["A"]})

    with pytest.raises(ValueError, match="IT"):
        analyze_it_keywords()

    mock_extract.assert_not_called()
    mock_merge.assert_not_called()


@patch("analyze_it_keywords._ollama_chat_json")
def test_pa_l3_itkw_007_extract_uses_ollama_json_response(
    mock_ollama_chat_json: MagicMock,
) -> None:
    """extract_it_keywords는 Ollama JSON dict를 ItKeywordResult로 검증한다."""
    mock_ollama_chat_json.return_value = {
        "summary": "summary",
        "flow": "release -> impact",
        "interest_label": "high",
        "keywords": ["PyTorch", "GPU"],
    }

    result = extract_it_keywords({"title": "PyTorch", "content": "GPU update"})

    mock_ollama_chat_json.assert_called_once()
    assert result == ItKeywordResult(
        summary="summary",
        flow="release -> impact",
        interest_label="high",
        keywords=["PyTorch", "GPU"],
    )
