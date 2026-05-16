from __future__ import annotations

from collections import Counter

from kag_graph.extraction.models import KeywordCandidate, MorphToken
from kag_graph.extraction.preprocessing.korean_morph_analyzer import ACTION_VERBS
from kag_graph.extraction.preprocessing.token_filter import MAX_PHRASE_LENGTH_CHARS


ALLOWED_BIGRAM_TAGS = {
    ("NNG", "NNG"),
    ("NNP", "NNP"),
    ("SL", "NNG"),
    ("NNG", "SL"),
    ("SL", "SN"),
}


class CandidatePhraseBuilder:
    def build(self, article_id: str, tokens: list[MorphToken], title: str, content: str) -> list[KeywordCandidate]:
        phrases = self._phrases(tokens)
        counts = Counter(phrases)
        candidates: list[KeywordCandidate] = []
        for phrase, count in counts.items():
            candidates.append(
                KeywordCandidate(
                    text=phrase,
                    article_id=article_id,
                    title_occurrences=title.count(phrase),
                    body_occurrences=max(content.count(phrase), count),
                )
            )
        return candidates

    def _phrases(self, tokens: list[MorphToken]) -> list[str]:
        phrases: list[str] = []
        keyword_tokens = [token for token in tokens if token.form not in ACTION_VERBS]
        for token in keyword_tokens:
            phrases.append(token.form)

        for size in (2, 3):
            for index in range(0, len(keyword_tokens) - size + 1):
                window = keyword_tokens[index:index + size]
                if size == 2 and not self._is_allowed_bigram(window):
                    continue
                phrase = " ".join(token.form for token in window)
                if len(phrase) <= MAX_PHRASE_LENGTH_CHARS:
                    phrases.append(phrase)
        return phrases

    def _is_allowed_bigram(self, tokens: list[MorphToken]) -> bool:
        return (tokens[0].tag, tokens[1].tag) in ALLOWED_BIGRAM_TAGS
