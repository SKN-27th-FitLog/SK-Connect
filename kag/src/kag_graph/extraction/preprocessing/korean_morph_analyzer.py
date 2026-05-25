from __future__ import annotations

import re

from kiwipiepy import Kiwi

from kag_graph.extraction.models import MorphToken


ALLOWED_POS_PREFIXES = ("NNG", "NNP", "SL", "SN", "SH")
ACTION_VERBS = {"출시", "공개", "발표", "배포", "인수", "합병", "제휴", "투자", "해킹", "유출"}


class KoreanMorphAnalyzer:
    def __init__(self, kiwi: Kiwi | None = None):
        self._kiwi = kiwi or Kiwi()

    def analyze(self, text: str) -> list[MorphToken]:
        tokens: list[MorphToken] = []
        for token in self._kiwi.tokenize(text):
            form = token.form.strip()
            tag = token.tag
            if not form:
                continue
            if tag.startswith(ALLOWED_POS_PREFIXES) or form in ACTION_VERBS:
                tokens.append(MorphToken(form=form, tag=tag))

        return _add_ascii_terms(text, tokens)


def _add_ascii_terms(text: str, tokens: list[MorphToken]) -> list[MorphToken]:
    existing = {token.form for token in tokens}
    result = list(tokens)
    for match in re.finditer(r"[A-Za-z][A-Za-z0-9+.-]*", text):
        term = match.group(0)
        normalized = term.split("-")[0]
        if normalized and normalized not in existing:
            result.append(MorphToken(form=normalized, tag="SL"))
            existing.add(normalized)
    return result
