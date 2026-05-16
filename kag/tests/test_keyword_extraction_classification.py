import pytest

from kag_graph.extraction.dictionary_resolver import DictionaryEntry, DictionaryResolver
from kag_graph.extraction.llm_client import create_llm_classifier
from kag_graph.extraction.models import KeywordCandidate, MalformedReason, ReviewReason
from kag_graph.extraction.providers.mock_llm_client import MockLLMKeywordClassifier
from kag_graph.extraction.providers.ollama_client import OllamaKeywordClassifier
from kag_graph.extraction.response_parser import ResponseParser


def test_dictionary_resolver_matches_alias_and_reports_conflict():
    resolver = DictionaryResolver(
        [
            DictionaryEntry("OpenAI", "Company", ("openai", "chatgpt 개발사")),
            DictionaryEntry("ChatGPT", "Technology", ("chatgpt",)),
            DictionaryEntry("OtherGPT", "Technology", ("chatgpt",)),
        ]
    )
    candidates = [
        KeywordCandidate(" openai ", "a1", body_occurrences=1, importance_score=0.9),
        KeywordCandidate("chatgpt", "a1", body_occurrences=1, importance_score=0.8),
        KeywordCandidate("unknown", "a1", body_occurrences=1, importance_score=0.7),
    ]

    result = resolver.resolve(candidates)

    assert result.resolved[0].canonical_name == "OpenAI"
    assert result.resolved[0].source == "dictionary"
    assert [candidate.text for candidate in result.unresolved] == ["chatgpt", "unknown"]
    assert result.review_reasons == [ReviewReason.DICTIONARY_ALIAS_CONFLICT]


def test_mock_llm_classifier_classifies_keywords_without_extracting_new_ones():
    classifier = MockLLMKeywordClassifier(
        responses={
            "a1": [
                {
                    "canonical_name": "GPT-5",
                    "matched_keyword": "GPT-5",
                    "node_type": "Technology",
                    "classification_confidence": 0.8,
                }
            ]
        }
    )

    keywords = classifier.classify("a1", [KeywordCandidate("GPT-5", "a1", importance_score=0.7)], title="제목", content="본문")

    assert len(keywords) == 1
    assert keywords[0].canonical_name == "GPT-5"
    assert keywords[0].importance_score == 0.7
    assert keywords[0].source == "llm"


def test_response_parser_extracts_json_block_and_fails_unparseable_response():
    parser = ResponseParser()

    parsed = parser.parse('prefix ```json\n{"article_id": "a1", "keywords": []}\n``` suffix')

    assert parsed == {"article_id": "a1", "keywords": []}
    with pytest.raises(ValueError, match=MalformedReason.LLM_RESPONSE_PARSE_FAILED):
        parser.parse("not-json")


def test_llm_failure_fallback_keeps_dictionary_keywords_only():
    dictionary_keyword = DictionaryResolver(
        [DictionaryEntry("OpenAI", "Company", ("openai",))]
    ).resolve([KeywordCandidate("OpenAI", "a1", importance_score=0.9)]).resolved[0]
    classifier = MockLLMKeywordClassifier(should_fail=True)

    result = classifier.classify_with_fallback(
        article_id="a1",
        unresolved_candidates=[KeywordCandidate("unknown", "a1", importance_score=0.6)],
        dictionary_keywords=[dictionary_keyword],
        title="제목",
        content="본문",
    )

    assert result.keywords == [dictionary_keyword]
    assert result.review_reasons == [ReviewReason.LLM_CLASSIFICATION_FAILED]


def test_llm_provider_factory_selects_mock_and_ollama_from_config():
    mock = create_llm_classifier({"LLM_PROVIDER": "mock"})
    ollama = create_llm_classifier(
        {
            "LLM_PROVIDER": "ollama",
            "LLM_MODEL": "gemma",
            "LLM_TIMEOUT_SECONDS": "20",
            "LLM_RETRY_COUNT": "1",
        }
    )

    assert isinstance(mock, MockLLMKeywordClassifier)
    assert isinstance(ollama, OllamaKeywordClassifier)
    assert ollama.model == "gemma"
