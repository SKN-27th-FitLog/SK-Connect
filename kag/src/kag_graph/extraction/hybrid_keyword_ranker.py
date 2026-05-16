from __future__ import annotations

from dataclasses import dataclass
from math import log

from kag_graph.extraction.corpus_context_builder import CorpusContext
from kag_graph.extraction.models import KeywordCandidate, RANKING_METHOD, ReviewReason


MAX_KEYWORDS_PER_ARTICLE = 10
MIN_IMPORTANCE_SCORE = 0.15


@dataclass(frozen=True)
class KeywordRankingResult:
    keywords: list[KeywordCandidate]
    review_reasons: list[str]
    ranking_method: str = RANKING_METHOD


class HybridKeywordRanker:
    def rank(
        self,
        article_id: str,
        candidates: list[KeywordCandidate],
        corpus_context: CorpusContext,
    ) -> KeywordRankingResult:
        scored = [
            self._score_candidate(candidate, corpus_context)
            for candidate in candidates
            if candidate.article_id == article_id
        ]
        filtered = [candidate for candidate in scored if candidate.importance_score >= MIN_IMPORTANCE_SCORE]
        ranked = [
            candidate
            for _, candidate in sorted(
                enumerate(filtered),
                key=lambda item: (-item[1].importance_score, item[0]),
            )
        ][:MAX_KEYWORDS_PER_ARTICLE]

        review_reasons = list(corpus_context.review_reasons)
        if len(ranked) < 3:
            review_reasons.append(ReviewReason.LOW_KEYWORD_COUNT)

        return KeywordRankingResult(keywords=ranked, review_reasons=_dedupe(review_reasons))

    def _score_candidate(self, candidate: KeywordCandidate, corpus_context: CorpusContext) -> KeywordCandidate:
        tfidf_score = self._tfidf(candidate, corpus_context)
        textrank_score = min(1.0, candidate.total_occurrences / 5)
        title_boost = 1.0 if candidate.title_occurrences else 0.0
        final_score = (0.5 * tfidf_score) + (0.3 * textrank_score) + (0.2 * title_boost)
        return KeywordCandidate(
            text=candidate.text,
            article_id=candidate.article_id,
            title_occurrences=candidate.title_occurrences,
            body_occurrences=candidate.body_occurrences,
            importance_score=round(final_score, 6),
        )

    def _tfidf(self, candidate: KeywordCandidate, corpus_context: CorpusContext) -> float:
        if not corpus_context.documents:
            return 0.0
        document_frequency = sum(1 for document in corpus_context.documents if candidate.text in document)
        idf = log((1 + corpus_context.document_count) / (1 + document_frequency)) + 1
        return min(1.0, candidate.total_occurrences * idf / 5)


def _dedupe(values: list[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        if value not in result:
            result.append(value)
    return result
