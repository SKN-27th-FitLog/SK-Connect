import pytest

from kag_graph.extraction.models import (
    ClassifiedKeyword,
    EventSignal,
    ExtractionMetrics,
    MalformedArticleRecord,
    MalformedReason,
    NormalizedArticle,
    ReviewReason,
)


def test_normalized_article_requires_documented_boundary_fields():
    record = {
        "schema_version": "news.article.v1",
        "article_id": "IT_20260512_GEEKNEWS_000001",
        "source": "geeknews",
        "category_cd": "IC02",
        "title": "기사 제목",
        "content": "기사 본문",
        "url": "https://example.com/article",
        "content_hash": "sha256_hash",
        "batch_id": "20260512_IC02_001",
        "run_attempt": 1,
    }

    article = NormalizedArticle.from_dict(record)

    assert article.article_id == "IT_20260512_GEEKNEWS_000001"
    assert article.document_text == "기사 제목\n기사 본문"


def test_normalized_article_rejects_empty_title_and_content():
    with pytest.raises(ValueError, match=MalformedReason.EMPTY_TITLE):
        NormalizedArticle.from_dict(
            {
                "schema_version": "news.article.v1",
                "article_id": "article-1",
                "source": "geeknews",
                "category_cd": "IC02",
                "title": "",
                "content": "본문",
                "batch_id": "batch-1",
                "run_attempt": 1,
            }
        )

    with pytest.raises(ValueError, match=MalformedReason.EMPTY_CONTENT):
        NormalizedArticle.from_dict(
            {
                "schema_version": "news.article.v1",
                "article_id": "article-1",
                "source": "geeknews",
                "category_cd": "IC02",
                "title": "제목",
                "content": " ",
                "batch_id": "batch-1",
                "run_attempt": 1,
            }
        )


def test_review_and_malformed_reason_codes_match_design_document():
    assert ReviewReason.LOW_KEYWORD_COUNT == "LOW_KEYWORD_COUNT"
    assert ReviewReason.SMALL_CORPUS_SIZE == "SMALL_CORPUS_SIZE"
    assert ReviewReason.DICTIONARY_ALIAS_CONFLICT == "DICTIONARY_ALIAS_CONFLICT"
    assert ReviewReason.LLM_CLASSIFICATION_FAILED == "LLM_CLASSIFICATION_FAILED"
    assert ReviewReason.ALL_KEYWORDS_IGNORED == "ALL_KEYWORDS_IGNORED"
    assert ReviewReason.LOW_CONFIDENCE_KEYWORD == "LOW_CONFIDENCE_KEYWORD"

    assert MalformedReason.LLM_CLASSIFICATION_FAILED == "LLM_CLASSIFICATION_FAILED"
    assert MalformedReason.LLM_RESPONSE_PARSE_FAILED == "LLM_RESPONSE_PARSE_FAILED"
    assert MalformedReason.ARTICLE_ID_MISMATCH == "ARTICLE_ID_MISMATCH"


def test_keyword_extraction_record_serializes_documented_shape():
    article = NormalizedArticle.from_dict(
        {
            "schema_version": "news.article.v1",
            "article_id": "article-1",
            "source": "geeknews",
            "category_cd": "IC02",
            "title": "OpenAI 출시",
            "content": "ChatGPT 기능 출시",
            "url": "https://example.com/a",
            "content_hash": "hash",
            "batch_id": "batch-1",
            "run_attempt": 2,
        }
    )
    keyword = ClassifiedKeyword(
        canonical_name="OpenAI",
        matched_keyword="ChatGPT",
        node_type="Company",
        importance_score=0.94,
        classification_confidence=1.0,
        source="dictionary",
    )
    signal = EventSignal(
        action_type="RELEASE",
        matched_text="출시",
        confidence=0.8,
        source="morph_action_dictionary",
    )

    record = article.to_extraction_record(
        keywords=[keyword],
        event_signals=[signal],
        review_required=True,
        review_reasons=[ReviewReason.LOW_KEYWORD_COUNT],
        created_at="2026-05-13T21:30:12+09:00",
    )

    assert record.to_dict() == {
        "schema_version": "news.keyword_extraction.v3",
        "article_id": "article-1",
        "source": "geeknews",
        "category_cd": "IC02",
        "title": "OpenAI 출시",
        "url": "https://example.com/a",
        "published_at": None,
        "content_hash": "hash",
        "keywords": [
            {
                "canonical_name": "OpenAI",
                "matched_keyword": "ChatGPT",
                "node_type": "Company",
                "importance_score": 0.94,
                "classification_confidence": 1.0,
                "source": "dictionary",
            }
        ],
        "event_signals": [
            {
                "action_type": "RELEASE",
                "matched_text": "출시",
                "confidence": 0.8,
                "source": "morph_action_dictionary",
            }
        ],
        "keyword_count": 1,
        "ranking_method": "tfidf_textrank_hybrid_v1",
        "review_required": True,
        "review_reasons": ["LOW_KEYWORD_COUNT"],
        "batch_id": "batch-1",
        "run_attempt": 2,
        "created_at": "2026-05-13T21:30:12+09:00",
    }


def test_malformed_record_and_metrics_serialize_operational_state():
    malformed = MalformedArticleRecord(
        article_id="article-1",
        batch_id="batch-1",
        run_attempt=1,
        reason_code=MalformedReason.LLM_RESPONSE_PARSE_FAILED,
        message="json parse failed",
    )
    metrics = ExtractionMetrics(
        total_article_count=3,
        success_article_count=2,
        malformed_article_count=1,
        review_required_count=1,
        total_keyword_count=5,
    )

    assert malformed.to_dict()["reason_code"] == "LLM_RESPONSE_PARSE_FAILED"
    assert metrics.to_dict()["status"] == "PARTIAL_SUCCESS"
