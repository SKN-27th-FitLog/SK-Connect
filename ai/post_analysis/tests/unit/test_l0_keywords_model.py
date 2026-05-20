"""PA-L0-LLM: analyze_keywords_by_llm.Keywords Pydantic (Level 0)."""

from analyze_keywords_by_llm import Keywords


def test_pa_l0_llm_001_keywords_field() -> None:
    """PA-L0-LLM-001 [정상]: Keywords 스키마에 keywords 문자열 파싱."""
    m = Keywords(keywords="#a#b")
    assert m.keywords == "#a#b"


def test_pa_l0_llm_002_default_empty() -> None:
    """PA-L0-LLM-002 [경계]: keywords 미지정 시 빈 문자열 기본값."""
    assert Keywords().keywords == ""
