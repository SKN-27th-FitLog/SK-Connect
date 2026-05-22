"""PA-L0-CST: common.constant (Level 0, 불변 규칙)."""

from common.constant import (
    AnalysisColumn,
    AnalyzeKeywordsByLlmConfig,
    CodeTable,
    CrawlingColumn,
)


def test_pa_l0_cst_001_code_table() -> None:
    """PA-L0-CST-001 [불변]: CodeTable CA07/IC01/IC02 코드값."""
    assert CodeTable.CATEGORY_ETC.value == "CA07"
    assert CodeTable.INFORMATION_IT_INFO.value == "IC02"
    assert CodeTable.INFORMATION_RESTAURANT.value == "IC01"


def test_pa_l0_cst_002_allowed_crawling_excludes_internal() -> None:
    """PA-L0-CST-002 [불변]: allowed_crawling_columns에서 STATE·ERROR 제외."""
    allowed = CrawlingColumn.allowed_crawling_columns()
    assert CrawlingColumn.STATE.value not in allowed
    assert CrawlingColumn.ERROR.value not in allowed


def test_pa_l0_cst_003_allowed_analysis_includes_merge_keys() -> None:
    """PA-L0-CST-003 [불변]: allowed_analysis_columns에 MERGE 키 컬럼 포함."""
    allowed = AnalysisColumn.allowed_analysis_columns()
    assert AnalysisColumn.CRAWLING_ID.value in allowed
    assert AnalysisColumn.KEYWORDS.value in allowed


def test_pa_l0_cst_004_llm_empty_placeholders() -> None:
    """PA-L0-CST-004 [불변]: LLM content 빈 값 placeholder 튜플."""
    assert "" in AnalyzeKeywordsByLlmConfig.CONTENT_EMPTY_PLACEHOLDERS
    assert "-" in AnalyzeKeywordsByLlmConfig.CONTENT_EMPTY_PLACEHOLDERS
    assert "N/A" in AnalyzeKeywordsByLlmConfig.CONTENT_EMPTY_PLACEHOLDERS
