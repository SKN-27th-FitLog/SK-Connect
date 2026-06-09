"""PA-L0-ITKW: IC02 회사/분류 키워드 순수 로직."""

from common.it_company_registry import (
    build_company_keyword_values,
    match_it_companies,
)
from analyze_it_keywords import normalize_it_keywords


def test_pa_l0_itkw_001_company_registry_matches_alias_case_insensitive() -> None:
    """PA-L0-ITKW-001 [정상]: 회사 alias는 대소문자와 한글 별칭을 처리한다."""
    matches = match_it_companies(
        title="OpenAI and NVIDIA announce new AI infrastructure",
        content="chatgpt 개발사와 nvidia가 GPU 생태계를 확장했다.",
    )

    assert [company.canonical_name for company in matches] == ["OpenAI", "NVIDIA"]
    assert [company.company_type for company in matches] == ["ai_company", "semiconductor"]


def test_pa_l0_itkw_002_company_keywords_flatten_name_and_type_once() -> None:
    """PA-L0-ITKW-002 [정상]: 회사명과 회사 분류는 한 번만 flat list로 저장된다."""
    matches = match_it_companies(
        title="OpenAI OpenAI",
        content="ChatGPT 개발사 OpenAI가 새 모델을 공개했다.",
    )

    assert build_company_keyword_values(matches) == ["OpenAI", "ai_company"]
    assert normalize_it_keywords(build_company_keyword_values(matches)) == "#OpenAI#ai_company"


def test_pa_l0_itkw_003_company_registry_keeps_document_priority() -> None:
    """PA-L0-ITKW-003 [정상]: 매칭 결과는 설계서 회사 사전 순서를 따른다."""
    matches = match_it_companies(
        title="Anthropic and OpenAI expand model training",
        content="Microsoft also joined the infrastructure update.",
    )

    assert [company.canonical_name for company in matches] == [
        "OpenAI",
        "Anthropic",
        "Microsoft",
    ]
    assert normalize_it_keywords(build_company_keyword_values(matches)) == (
        "#OpenAI#ai_company#Anthropic#ai_company#Microsoft#bigtech"
    )


def test_pa_l0_itkw_004_company_registry_returns_empty_for_unknown_text() -> None:
    """PA-L0-ITKW-004 [경계]: 사전에 없는 회사만 있으면 빈 목록을 반환한다."""
    assert match_it_companies(title="새로운 오픈소스 릴리스", content="회사명 언급 없음") == []
