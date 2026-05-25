from kag_graph.extraction.corpus_context_builder import CorpusContextBuilder
from kag_graph.extraction.hybrid_keyword_ranker import HybridKeywordRanker
from kag_graph.extraction.models import KeywordCandidate, NormalizedArticle, RANKING_METHOD, ReviewReason


def _article(article_id: str, title: str, content: str, batch_id: str = "batch-1") -> NormalizedArticle:
    return NormalizedArticle.from_dict(
        {
            "schema_version": "news.article.v1",
            "article_id": article_id,
            "source": "geeknews",
            "category_cd": "IC02",
            "title": title,
            "content": content,
            "batch_id": batch_id,
            "run_attempt": 1,
        }
    )


def test_corpus_context_builder_uses_batch_documents_and_marks_small_corpus():
    articles = [
        _article("a1", "OpenAI GPT", "ChatGPT 출시"),
        _article("a2", "클라우드 AI", "GPU 투자"),
    ]

    context = CorpusContextBuilder().build(articles)

    assert context.batch_id == "batch-1"
    assert context.document_count == 2
    assert context.review_reasons == [ReviewReason.SMALL_CORPUS_SIZE]


def test_hybrid_keyword_ranker_limits_to_top_10_and_records_method():
    candidates = [
        KeywordCandidate(text=f"keyword{i}", article_id="a1", title_occurrences=1 if i == 11 else 0, body_occurrences=i)
        for i in range(1, 13)
    ]
    context = CorpusContextBuilder().build([_article("a1", "keyword11", " ".join(c.text for c in candidates))])

    result = HybridKeywordRanker().rank("a1", candidates, context)

    assert result.ranking_method == RANKING_METHOD
    assert len(result.keywords) == 10
    assert result.keywords[0].text == "keyword11"


def test_hybrid_keyword_ranker_marks_low_keyword_count_after_filtering():
    candidates = [
        KeywordCandidate(text="OpenAI", article_id="a1", body_occurrences=1),
        KeywordCandidate(text="GPT", article_id="a1", body_occurrences=1),
    ]
    context = CorpusContextBuilder().build([_article("a1", "OpenAI", "GPT")])

    result = HybridKeywordRanker().rank("a1", candidates, context)

    assert [candidate.text for candidate in result.keywords] == ["OpenAI", "GPT"]
    assert ReviewReason.LOW_KEYWORD_COUNT in result.review_reasons
