from __future__ import annotations

from kag_graph.extraction.llm_client import LLMClassificationResult
from kag_graph.extraction.models import ClassifiedKeyword, KeywordCandidate, ReviewReason


class MockLLMKeywordClassifier:
    def __init__(self, responses: dict[str, list[dict]] | None = None, should_fail: bool = False):
        self._responses = responses or {}
        self._should_fail = should_fail

    def classify(
        self,
        article_id: str,
        candidates: list[KeywordCandidate],
        title: str,
        content: str,
    ) -> list[ClassifiedKeyword]:
        if self._should_fail:
            raise RuntimeError("LLM classification failed")

        by_text = {candidate.text: candidate for candidate in candidates}
        response_rows = self._responses.get(article_id, [])
        keywords: list[ClassifiedKeyword] = []
        for row in response_rows:
            matched_keyword = str(row["matched_keyword"]).strip()
            candidate = by_text.get(matched_keyword)
            if candidate is None:
                continue
            keywords.append(
                ClassifiedKeyword(
                    canonical_name=str(row["canonical_name"]).strip(),
                    matched_keyword=matched_keyword,
                    node_type=str(row["node_type"]).strip(),
                    importance_score=candidate.importance_score,
                    classification_confidence=float(row["classification_confidence"]),
                    source="llm",
                )
            )
        return keywords

    def classify_with_fallback(
        self,
        article_id: str,
        unresolved_candidates: list[KeywordCandidate],
        dictionary_keywords: list[ClassifiedKeyword],
        title: str,
        content: str,
    ) -> LLMClassificationResult:
        try:
            llm_keywords = self.classify(article_id, unresolved_candidates, title, content)
        except Exception:
            return LLMClassificationResult(
                keywords=dictionary_keywords,
                review_reasons=[ReviewReason.LLM_CLASSIFICATION_FAILED],
            )
        return LLMClassificationResult(keywords=[*dictionary_keywords, *llm_keywords], review_reasons=[])
