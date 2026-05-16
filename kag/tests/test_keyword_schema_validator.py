import pytest

from kag_graph.extraction.keyword_schema_validator import KeywordSchemaValidator
from kag_graph.extraction.models import ClassifiedKeyword, MalformedReason, ReviewReason


def _keyword(name: str, node_type: str = "Technology", confidence: float = 0.9) -> ClassifiedKeyword:
    return ClassifiedKeyword(
        canonical_name=name,
        matched_keyword=name,
        node_type=node_type,
        importance_score=0.5,
        classification_confidence=confidence,
        source="llm",
    )


def test_validator_removes_ignore_and_low_confidence_keywords():
    result = KeywordSchemaValidator().validate(
        article_id="a1",
        keywords=[
            _keyword("GPT", confidence=0.9),
            _keyword("일반", node_type="Ignore", confidence=0.9),
            _keyword("낮음", confidence=0.49),
        ],
        document_count=10,
        prior_review_reasons=[],
    )

    assert [keyword.canonical_name for keyword in result.keywords] == ["GPT"]


def test_validator_marks_low_confidence_and_low_keyword_count_review():
    result = KeywordSchemaValidator().validate(
        article_id="a1",
        keywords=[_keyword("GPT", confidence=0.7), _keyword("OpenAI", "Company", 0.9)],
        document_count=10,
        prior_review_reasons=[],
    )

    assert result.review_required is True
    assert ReviewReason.LOW_CONFIDENCE_KEYWORD in result.review_reasons
    assert ReviewReason.LOW_KEYWORD_COUNT in result.review_reasons


def test_validator_marks_all_keywords_ignored_after_ignore_removal():
    result = KeywordSchemaValidator().validate(
        article_id="a1",
        keywords=[_keyword("일반", node_type="Ignore", confidence=0.9)],
        document_count=10,
        prior_review_reasons=[],
    )

    assert result.keywords == []
    assert result.review_reasons == [ReviewReason.ALL_KEYWORDS_IGNORED]


def test_validator_rejects_unrecoverable_article_mismatch_and_non_list_keywords():
    validator = KeywordSchemaValidator()

    with pytest.raises(ValueError, match=MalformedReason.ARTICLE_ID_MISMATCH):
        validator.validate_llm_payload("a1", {"article_id": "a2", "keywords": []})

    with pytest.raises(ValueError, match=MalformedReason.VALIDATOR_FAILED):
        validator.validate_llm_payload("a1", {"article_id": "a1", "keywords": {}})
