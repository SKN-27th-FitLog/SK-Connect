from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from kag_graph.extraction.models import ALLOWED_NODE_TYPES, ClassifiedKeyword, MalformedReason, NodeType, ReviewReason


LOW_CONFIDENCE_THRESHOLD = 0.50
NORMAL_CONFIDENCE_THRESHOLD = 0.75
MIN_KEYWORD_COUNT = 3
MIN_DOCUMENT_COUNT = 10


@dataclass(frozen=True)
class KeywordValidationResult:
    keywords: list[ClassifiedKeyword]
    review_required: bool
    review_reasons: list[str]


class KeywordSchemaValidator:
    def validate(
        self,
        article_id: str,
        keywords: list[ClassifiedKeyword],
        document_count: int,
        prior_review_reasons: list[str],
    ) -> KeywordValidationResult:
        accepted: list[ClassifiedKeyword] = []
        review_reasons = list(prior_review_reasons)
        ignored_count = 0

        for keyword in keywords:
            if keyword.node_type == NodeType.IGNORE:
                ignored_count += 1
                continue
            if keyword.node_type not in ALLOWED_NODE_TYPES:
                continue
            if not keyword.canonical_name.strip() or not keyword.matched_keyword.strip():
                continue
            if keyword.classification_confidence < LOW_CONFIDENCE_THRESHOLD:
                continue
            if keyword.classification_confidence < NORMAL_CONFIDENCE_THRESHOLD:
                review_reasons.append(ReviewReason.LOW_CONFIDENCE_KEYWORD)
            accepted.append(keyword)

        accepted = self._dedupe(accepted)
        if not accepted and ignored_count:
            review_reasons.append(ReviewReason.ALL_KEYWORDS_IGNORED)
        elif len(accepted) < MIN_KEYWORD_COUNT:
            review_reasons.append(ReviewReason.LOW_KEYWORD_COUNT)
        if document_count < MIN_DOCUMENT_COUNT:
            review_reasons.append(ReviewReason.SMALL_CORPUS_SIZE)

        review_reasons = _dedupe(review_reasons)
        return KeywordValidationResult(
            keywords=accepted,
            review_required=bool(review_reasons),
            review_reasons=review_reasons,
        )

    def validate_llm_payload(self, article_id: str, payload: dict[str, Any]) -> None:
        if payload.get("article_id") != article_id:
            raise ValueError(MalformedReason.ARTICLE_ID_MISMATCH)
        if not isinstance(payload.get("keywords"), list):
            raise ValueError(MalformedReason.VALIDATOR_FAILED)

    def _dedupe(self, keywords: list[ClassifiedKeyword]) -> list[ClassifiedKeyword]:
        result: list[ClassifiedKeyword] = []
        seen: set[tuple[str, str]] = set()
        for keyword in keywords:
            key = (keyword.node_type, keyword.canonical_name)
            if key in seen:
                continue
            seen.add(key)
            result.append(keyword)
        return result


def _dedupe(values: list[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        if value not in result:
            result.append(value)
    return result
