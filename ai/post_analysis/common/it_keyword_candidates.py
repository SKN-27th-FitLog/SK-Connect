"""IC02 IT 키워드 후보군 추출과 LLM 결과 검증."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import re

from kiwipiepy import Kiwi

from common.constant import AnalyzeItKeywordsConfig


@dataclass(frozen=True)
class ItKeywordCandidate:
    """원문 기반 IC02 키워드 후보."""

    text: str
    score: int
    source: str
    frequency: int


_KIWI: Kiwi | None = None
_TECH_PATTERN = re.compile(r"[A-Za-z][A-Za-z0-9]*(?:[-_.][A-Za-z0-9]+)*|\d+(?:\.\d+)*")
_EDGE_PUNCTUATION = " \t\r\n\v\f,.;:!?()[]{}<>\"'“”‘’`~"


def _get_kiwi() -> Kiwi:
    """KiWi 인스턴스를 지연 생성한다."""
    global _KIWI
    if _KIWI is None:
        _KIWI = Kiwi()
    return _KIWI


def _normalize_candidate_text(text: str) -> str:
    """후보 비교용 문자열을 정규화한다."""
    normalized = re.sub(r"\s+", " ", str(text or "").strip())
    return normalized.strip(_EDGE_PUNCTUATION)


def _candidate_key(text: str) -> str:
    """대소문자 차이를 무시한 후보 key를 만든다."""
    return _normalize_candidate_text(text).casefold()


def _contains_tech_pattern(text: str) -> bool:
    """영문 기술명, 버전, 숫자 패턴 포함 여부를 반환한다."""
    return bool(_TECH_PATTERN.search(text))


def _is_stopword(text: str) -> bool:
    """일반어·저품질 표현을 후보에서 제외한다."""
    normalized = _normalize_candidate_text(text)
    if not normalized:
        return True
    if normalized in AnalyzeItKeywordsConfig.CANDIDATE_STOPWORDS:
        return True
    parts = normalized.split()
    return bool(parts) and all(part in AnalyzeItKeywordsConfig.CANDIDATE_STOPWORDS for part in parts)


def _is_valid_candidate(text: str) -> bool:
    """최종 후보로 보관할 수 있는 문자열인지 검증한다."""
    normalized = _normalize_candidate_text(text)
    if len(normalized) < AnalyzeItKeywordsConfig.CANDIDATE_MIN_KEYWORD_CHARS:
        return False
    if len(normalized) > AnalyzeItKeywordsConfig.CANDIDATE_MAX_KEYWORD_CHARS:
        return False
    if normalized.isnumeric():
        return False
    return not _is_stopword(normalized)


def _token_is_candidate_part(token: object) -> bool:
    """KiWi token이 후보 명사구 구성 재료인지 판단한다."""
    return getattr(token, "tag", "") in AnalyzeItKeywordsConfig.CANDIDATE_NOUN_POS_TAGS


def _extract_runs(text: str) -> list[list[object]]:
    """후보 재료 token의 연속 구간을 추출한다."""
    runs: list[list[object]] = []
    current: list[object] = []
    for token in _get_kiwi().tokenize(text):
        if _token_is_candidate_part(token):
            current.append(token)
            continue
        if current:
            runs.append(current)
            current = []
    if current:
        runs.append(current)
    return runs


def _surface_from_tokens(text: str, tokens: list[object]) -> str:
    """연속 token 구간의 원문 표면형을 반환한다."""
    start = int(getattr(tokens[0], "start"))
    end = int(getattr(tokens[-1], "end"))
    return _normalize_candidate_text(text[start:end])


def _candidate_texts_from_text(text: str) -> list[str]:
    """KiWi token run과 영문 패턴에서 원문 표면형 후보를 만든다."""
    candidates: list[str] = []
    for run in _extract_runs(text):
        max_window = min(3, len(run))
        for window in range(max_window, 0, -1):
            for start in range(0, len(run) - window + 1):
                surface = _surface_from_tokens(text, run[start : start + window])
                if _is_valid_candidate(surface):
                    candidates.append(surface)
    for match in _TECH_PATTERN.finditer(text):
        surface = _normalize_candidate_text(match.group(0))
        if _is_valid_candidate(surface):
            candidates.append(surface)
    return candidates


def _source_for_candidate(key: str, title_keys: set[str], content_keys: set[str]) -> str:
    """후보 출처를 title/content/both로 분류한다."""
    if key in title_keys and key in content_keys:
        return "both"
    if key in title_keys:
        return "title"
    return "content"


def _has_important_term(text: str) -> bool:
    """IC02 중요 기술 용어 포함 여부를 반환한다."""
    lowered = text.lower()
    return any(term.lower() in lowered for term in AnalyzeItKeywordsConfig.IMPORTANT_TERMS)


def _has_signal_nearby(text: str, content: str) -> bool:
    """후보 주변에 변화·효과 신호가 있는지 확인한다."""
    normalized = _normalize_candidate_text(text)
    content_text = str(content or "")
    index = content_text.find(normalized)
    if index < 0:
        return False
    left = max(index - 40, 0)
    right = min(index + len(normalized) + 40, len(content_text))
    window = content_text[left:right]
    return any(term in window for term in AnalyzeItKeywordsConfig.CANDIDATE_SIGNAL_TERMS)


def _score_candidate(
    text: str,
    *,
    frequency: int,
    source: str,
    title: str,
    content: str,
) -> int:
    """후보 중요도를 deterministic 점수로 계산한다."""
    normalized = _normalize_candidate_text(text)
    score = frequency * AnalyzeItKeywordsConfig.CANDIDATE_FREQUENCY_WEIGHT
    token_count = len(normalized.split())
    if token_count > 1:
        score += min(token_count - 1, 2) * AnalyzeItKeywordsConfig.CANDIDATE_TECH_PATTERN_WEIGHT
    if source in {"title", "both"}:
        score += AnalyzeItKeywordsConfig.CANDIDATE_TITLE_WEIGHT
    content_index = str(content or "").find(text)
    if 0 <= content_index <= 300:
        score += AnalyzeItKeywordsConfig.CANDIDATE_EARLY_CONTENT_WEIGHT
    if _contains_tech_pattern(text):
        score += AnalyzeItKeywordsConfig.CANDIDATE_TECH_PATTERN_WEIGHT
    if _has_important_term(text):
        score += AnalyzeItKeywordsConfig.CANDIDATE_IMPORTANT_TERM_WEIGHT
    if _has_signal_nearby(text, content):
        score += AnalyzeItKeywordsConfig.CANDIDATE_SIGNAL_NEARBY_WEIGHT
    return score


def extract_it_keyword_candidates(title: object, content: object) -> list[ItKeywordCandidate]:
    """title과 content에서 원문 기반 IC02 키워드 후보를 추출한다."""
    title_text = str(title or "")
    content_text = str(content or "")
    title_candidates = _candidate_texts_from_text(title_text)
    content_candidates = _candidate_texts_from_text(content_text)
    all_candidates = title_candidates + content_candidates
    counts = Counter(_candidate_key(candidate) for candidate in all_candidates)
    title_keys = {_candidate_key(candidate) for candidate in title_candidates}
    content_keys = {_candidate_key(candidate) for candidate in content_candidates}

    canonical: dict[str, str] = {}
    for candidate in all_candidates:
        key = _candidate_key(candidate)
        if key and key not in canonical:
            canonical[key] = _normalize_candidate_text(candidate)

    out: list[ItKeywordCandidate] = []
    for key, frequency in counts.items():
        text = canonical[key]
        source = _source_for_candidate(key, title_keys, content_keys)
        score = _score_candidate(
            text,
            frequency=frequency,
            source=source,
            title=title_text,
            content=content_text,
        )
        if score < AnalyzeItKeywordsConfig.MIN_CANDIDATE_SCORE:
            continue
        out.append(
            ItKeywordCandidate(
                text=text,
                score=score,
                source=source,
                frequency=frequency,
            )
        )
    return sorted(out, key=lambda candidate: (-candidate.score, -candidate.frequency, candidate.text.casefold()))


def format_candidate_keywords_for_prompt(
    candidates: list[ItKeywordCandidate],
    limit: int = AnalyzeItKeywordsConfig.MAX_PROMPT_CANDIDATES,
) -> str:
    """LLM prompt에 넣을 후보군 문자열을 만든다."""
    return "\n".join(candidate.text for candidate in candidates[:limit])


def filter_it_keywords_by_candidates(
    keywords: object,
    candidates: list[ItKeywordCandidate],
) -> list[str]:
    """LLM 키워드를 원문 후보군에 있는 값으로만 제한한다."""
    if isinstance(keywords, str):
        parts = keywords.split("#") if "#" in keywords else [keywords]
    elif isinstance(keywords, list):
        parts = keywords
    else:
        parts = []

    allowed = {_candidate_key(candidate.text): candidate.text for candidate in candidates}
    seen: set[str] = set()
    filtered: list[str] = []
    for part in parts:
        key = _candidate_key(str(part))
        if not key or key in seen or key not in allowed:
            continue
        seen.add(key)
        filtered.append(allowed[key])
    return filtered
