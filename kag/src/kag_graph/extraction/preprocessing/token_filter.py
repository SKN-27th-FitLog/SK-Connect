from __future__ import annotations

from kag_graph.extraction.models import MorphToken
from kag_graph.extraction.preprocessing.korean_morph_analyzer import ACTION_VERBS


STOPWORDS = {"그리고", "그러나", "대한", "관련", "기반", "이번"}
MAX_PHRASE_LENGTH_CHARS = 40


class TokenFilter:
    def filter(self, tokens: list[MorphToken]) -> list[MorphToken]:
        return [token for token in tokens if self._is_allowed(token)]

    def _is_allowed(self, token: MorphToken) -> bool:
        text = token.form.strip()
        if len(text) <= 1:
            return False
        if text.isdigit():
            return False
        if text in STOPWORDS:
            return False
        if len(text) > MAX_PHRASE_LENGTH_CHARS:
            return False
        if token.tag.startswith(("J", "E")):
            return False
        if token.tag.startswith("V") and text not in ACTION_VERBS:
            return False
        return True
