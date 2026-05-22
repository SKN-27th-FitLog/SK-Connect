"""PA-L3-LLM: analyze_keywords_by_llm 간접 검증 (chain·merge patch)."""

from unittest.mock import MagicMock, patch

import pandas as pd

from analyze_keywords_by_llm import Keywords, analyze_keywords_by_llm
from common.constant import AnalysisColumn, CodeTable


@patch("analyze_keywords_by_llm.merge_analysis_data")
@patch("analyze_keywords_by_llm.ChatOpenAI")
@patch("analyze_keywords_by_llm.get_analysis_data")
def test_pa_l3_llm_002_no_pending_rows(
    mock_get: MagicMock,
    mock_llm_cls: MagicMock,
    mock_merge: MagicMock,
) -> None:
    """PA-L3-LLM-002 [경계]: keywords가 모두 있으면 LLM·merge 미호출."""
    mock_get.return_value = pd.DataFrame(
        {
            AnalysisColumn.CONTENT.value: ["body"],
            AnalysisColumn.KEYWORDS.value: ["#already#"],
            AnalysisColumn.INFORMATION_CD.value: [CodeTable.INFORMATION_RESTAURANT.value],
            AnalysisColumn.SENTIMENTAL.value: ["positive"],
            AnalysisColumn.TITLE.value: ["t"],
        }
    )

    analyze_keywords_by_llm()
    mock_merge.assert_not_called()
    mock_llm_cls.assert_not_called()


@patch("analyze_keywords_by_llm.merge_analysis_data")
@patch("analyze_keywords_by_llm.PydanticOutputParser")
@patch("analyze_keywords_by_llm.PromptTemplate")
@patch("analyze_keywords_by_llm.ChatOpenAI")
@patch("analyze_keywords_by_llm.get_analysis_data")
def test_pa_l3_llm_006_merge_receives_keywords(
    mock_get: MagicMock,
    mock_llm_cls: MagicMock,
    mock_prompt_cls: MagicMock,
    mock_parser_cls: MagicMock,
    mock_merge: MagicMock,
) -> None:
    """PA-L3-LLM-006 [정상]: LLM 결과 keywords가 merge DataFrame에 반영(간접)."""
    mock_get.return_value = pd.DataFrame(
        {
            AnalysisColumn.CONTENT.value: ["맛있다"],
            AnalysisColumn.KEYWORDS.value: [pd.NA],
            AnalysisColumn.INFORMATION_CD.value: [CodeTable.INFORMATION_RESTAURANT.value],
            AnalysisColumn.SENTIMENTAL.value: ["positive"],
            AnalysisColumn.TITLE.value: ["title"],
        }
    )

    mock_parser = MagicMock()
    mock_parser.get_format_instructions.return_value = ""
    mock_parser_cls.return_value = mock_parser

    mock_chain = MagicMock()
    mock_chain.invoke.return_value = Keywords(keywords="#좋아요#")

    mock_mid = MagicMock()
    mock_mid.__or__ = MagicMock(return_value=mock_chain)
    mock_prompt = MagicMock()
    mock_prompt.__or__ = MagicMock(return_value=mock_mid)
    mock_prompt_cls.return_value = mock_prompt
    mock_llm_cls.return_value = MagicMock()

    analyze_keywords_by_llm(max_rows=None)

    mock_merge.assert_called_once()
    df = mock_merge.call_args[0][0]
    assert df[AnalysisColumn.KEYWORDS.value].iloc[0] == "#좋아요#"
