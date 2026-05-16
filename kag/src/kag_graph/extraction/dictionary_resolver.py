from __future__ import annotations

from dataclasses import dataclass

from kag_graph.extraction.models import ClassifiedKeyword, KeywordCandidate, ReviewReason


@dataclass(frozen=True)
class DictionaryEntry:
    canonical_name: str
    node_type: str
    aliases: tuple[str, ...]


@dataclass(frozen=True)
class DictionaryResolutionResult:
    resolved: list[ClassifiedKeyword]
    unresolved: list[KeywordCandidate]
    review_reasons: list[str]


class DictionaryResolver:
    def __init__(self, entries: list[DictionaryEntry] | None = None):
        self._entries = entries or []
        self._alias_map = self._build_alias_map(self._entries)

    def resolve(self, candidates: list[KeywordCandidate]) -> DictionaryResolutionResult:
        resolved: list[ClassifiedKeyword] = []
        unresolved: list[KeywordCandidate] = []
        review_reasons: list[str] = []

        for candidate in candidates:
            matches = self._alias_map.get(_normalize_alias(candidate.text), [])
            if len(matches) == 1:
                entry = matches[0]
                resolved.append(
                    ClassifiedKeyword(
                        canonical_name=entry.canonical_name,
                        matched_keyword=candidate.text.strip(),
                        node_type=entry.node_type,
                        importance_score=candidate.importance_score,
                        classification_confidence=1.0,
                        source="dictionary",
                    )
                )
                continue
            if len(matches) > 1 and ReviewReason.DICTIONARY_ALIAS_CONFLICT not in review_reasons:
                review_reasons.append(ReviewReason.DICTIONARY_ALIAS_CONFLICT)
            unresolved.append(candidate)

        return DictionaryResolutionResult(resolved=resolved, unresolved=unresolved, review_reasons=review_reasons)

    def _build_alias_map(self, entries: list[DictionaryEntry]) -> dict[str, list[DictionaryEntry]]:
        alias_map: dict[str, list[DictionaryEntry]] = {}
        for entry in entries:
            aliases = set(entry.aliases)
            aliases.add(entry.canonical_name)
            for alias in aliases:
                normalized = _normalize_alias(alias)
                bucket = alias_map.setdefault(normalized, [])
                if not any(existing.canonical_name == entry.canonical_name for existing in bucket):
                    bucket.append(entry)
        return alias_map


def _normalize_alias(value: str) -> str:
    return value.strip().casefold()
