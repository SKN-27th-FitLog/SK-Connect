"""PA-L0-CST: constant.py."""

from common.constant import (
    AnalysisColumn,
    AnalyzeKeywordsByLlmConfig,
    CodeTable,
    CrawlingColumn,
)


def test_pa_l0_cst_001_code_table() -> None:
    assert CodeTable.CATEGORY_ETC.value == "CA07"
    assert CodeTable.INFORMATION_IT_INFO.value == "IC02"
    assert CodeTable.INFORMATION_RESTAURANT.value == "IC01"


def test_pa_l0_cst_002_allowed_crawling_excludes_internal() -> None:
    allowed = CrawlingColumn.allowed_crawling_columns()
    assert CrawlingColumn.STATE.value not in allowed
    assert CrawlingColumn.ERROR.value not in allowed


def test_pa_l0_cst_003_allowed_analysis_includes_merge_keys() -> None:
    allowed = AnalysisColumn.allowed_analysis_columns()
    assert AnalysisColumn.CRAWLING_ID.value in allowed
    assert AnalysisColumn.KEYWORDS.value in allowed


def test_pa_l0_cst_004_llm_empty_placeholders() -> None:
    assert "" in AnalyzeKeywordsByLlmConfig.CONTENT_EMPTY_PLACEHOLDERS
    assert "-" in AnalyzeKeywordsByLlmConfig.CONTENT_EMPTY_PLACEHOLDERS
    assert "N/A" in AnalyzeKeywordsByLlmConfig.CONTENT_EMPTY_PLACEHOLDERS
