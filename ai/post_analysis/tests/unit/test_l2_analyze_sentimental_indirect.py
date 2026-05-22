"""PA-L2-SNT: analyze_sentimental 간접 검증 (get/merge/BERT patch)."""

from unittest.mock import MagicMock, patch

import pandas as pd

from analyze_sentimental import analyze_sentimental
from common.constant import AnalysisColumn, CodeTable, SentimentResultKey


@patch("analyze_sentimental.merge_analysis_data")
@patch("analyze_sentimental.BertTokenizer")
@patch("analyze_sentimental.get_analysis_data")
def test_pa_l2_snt_002_no_pending_rows(
    mock_get: MagicMock,
    mock_bert_cls: MagicMock,
    mock_merge: MagicMock,
) -> None:
    """PA-L2-SNT-002 [경계]: pending 0건이면 early return, merge·BERT 미호출."""
    mock_get.return_value = pd.DataFrame(
        {
            AnalysisColumn.CONTENT.value: ["c"],
            AnalysisColumn.SENTIMENTAL.value: ["positive"],
            AnalysisColumn.SCORE.value: [0.9],
            AnalysisColumn.INFORMATION_CD.value: [CodeTable.INFORMATION_RESTAURANT.value],
        }
    )

    analyze_sentimental()
    mock_merge.assert_not_called()
    mock_bert_cls.assert_not_called()


@patch("analyze_sentimental.merge_analysis_data")
@patch("analyze_sentimental.BertTokenizer")
@patch("analyze_sentimental.get_analysis_data")
def test_pa_l2_snt_003_excludes_ic02(
    mock_get: MagicMock,
    mock_bert_cls: MagicMock,
    mock_merge: MagicMock,
) -> None:
    """PA-L2-SNT-003 [불변]: IC02 제외·IC01 pending 1건만 merge·predict."""
    mock_get.return_value = pd.DataFrame(
        {
            AnalysisColumn.CONTENT.value: ["a", "b"],
            AnalysisColumn.SENTIMENTAL.value: [None, None],
            AnalysisColumn.SCORE.value: [None, None],
            AnalysisColumn.INFORMATION_CD.value: [
                CodeTable.INFORMATION_IT_INFO.value,
                CodeTable.INFORMATION_RESTAURANT.value,
            ],
        }
    )
    mock_inst = MagicMock()
    mock_inst.predict_sentiment.return_value = {
        SentimentResultKey.SENTIMENTAL.value: "positive",
        SentimentResultKey.SCORE.value: 0.9,
    }
    mock_bert_cls.return_value = mock_inst

    analyze_sentimental()

    mock_merge.assert_called_once()
    df = mock_merge.call_args[0][0]
    assert len(df) == 1
    assert df[AnalysisColumn.INFORMATION_CD.value].iloc[0] == CodeTable.INFORMATION_RESTAURANT.value
    mock_inst.predict_sentiment.assert_called_once()
