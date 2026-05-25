from __future__ import annotations

from dataclasses import dataclass

from kag_graph.extraction.models import NormalizedArticle, ReviewReason


MIN_CORPUS_DOCUMENT_COUNT = 10


@dataclass(frozen=True)
class CorpusContext:
    category_cd: str
    batch_id: str
    document_count: int
    documents: list[str]
    article_ids: list[str]
    corpus_version: str
    review_reasons: list[str]


class CorpusContextBuilder:
    def build(self, articles: list[NormalizedArticle]) -> CorpusContext:
        first = articles[0] if articles else None
        document_count = len(articles)
        review_reasons = []
        if document_count < MIN_CORPUS_DOCUMENT_COUNT:
            review_reasons.append(ReviewReason.SMALL_CORPUS_SIZE)

        return CorpusContext(
            category_cd=first.category_cd if first else "",
            batch_id=first.batch_id if first else "",
            document_count=document_count,
            documents=[article.document_text for article in articles],
            article_ids=[article.article_id for article in articles],
            corpus_version="batch_v1",
            review_reasons=review_reasons,
        )
