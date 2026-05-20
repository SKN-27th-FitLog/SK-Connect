"""PA-L0-LLM: Keywords Pydantic model."""

from analyze_keywords_by_llm import Keywords


def test_pa_l0_llm_001_keywords_field() -> None:
    m = Keywords(keywords="#a#b")
    assert m.keywords == "#a#b"


def test_pa_l0_llm_002_default_empty() -> None:
    assert Keywords().keywords == ""
