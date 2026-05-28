"""PA-L0-ITKW: IC02 IT keyword pure helpers and config."""

import pytest

from common.constant import AnalyzeItKeywordsConfig
from common.errors import PostAnalysisErrors


def test_pa_l0_itkw_001_config_defaults() -> None:
    """PA-L0-ITKW-001 [불변]: IC02 키워드 기본 모델과 관심도 기준."""
    assert AnalyzeItKeywordsConfig.DEFAULT_MODEL == "gemma4:26b"
    assert AnalyzeItKeywordsConfig.MODEL_ENV_KEY == "POST_ANALYSIS_IT_KEYWORDS_MODEL"
    assert AnalyzeItKeywordsConfig.OLLAMA_BASE_URL_ENV_KEY == "OLLAMA_BASE_URL"
    assert AnalyzeItKeywordsConfig.MAX_KEYWORDS == 7
    assert AnalyzeItKeywordsConfig.INTEREST_HIGH_THRESHOLD == 1000
    assert AnalyzeItKeywordsConfig.INTEREST_MEDIUM_THRESHOLD == 100


def test_pa_l0_itkw_002_error_messages() -> None:
    """PA-L0-ITKW-002 [정상]: IC02 키워드 오류 메시지가 독립 namespace에 있다."""
    assert "IT 키워드" in PostAnalysisErrors.ItKeywords.missing_columns(["title"])
    assert "처리할" in PostAnalysisErrors.ItKeywords.no_pending_rows()
    assert "crawling_id" in PostAnalysisErrors.ItKeywords.row_processing_failed()
