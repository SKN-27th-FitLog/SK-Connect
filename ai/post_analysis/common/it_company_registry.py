"""IC02 IT 회사 사전과 deterministic 매칭 로직."""

from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class ItCompany:
    """IC02 회사 키워드 저장에 필요한 최소 회사 정보."""

    canonical_name: str
    company_type: str
    aliases: tuple[str, ...]


IT_COMPANIES: tuple[ItCompany, ...] = (
    ItCompany("OpenAI", "ai_company", ("openai", "chatgpt 개발사")),
    ItCompany("Anthropic", "ai_company", ("anthropic", "claude 개발사")),
    ItCompany("Google", "bigtech", ("google", "구글", "alphabet")),
    ItCompany("Microsoft", "bigtech", ("microsoft", "ms", "마이크로소프트")),
    ItCompany("Apple", "bigtech", ("apple", "애플")),
    ItCompany("NVIDIA", "semiconductor", ("nvidia", "엔비디아")),
    ItCompany("Samsung", "semiconductor", ("samsung", "삼성", "삼성전자")),
)


def _text_or_empty(value: object) -> str:
    if value is None:
        return ""
    return str(value)


def _is_ascii_word_alias(alias: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9.+_-]*", alias))


def _contains_alias(text: str, alias: str) -> bool:
    if not alias:
        return False
    if _is_ascii_word_alias(alias):
        pattern = rf"(?<![A-Za-z0-9]){re.escape(alias)}(?![A-Za-z0-9])"
        return re.search(pattern, text, flags=re.IGNORECASE) is not None
    return alias.casefold() in text.casefold()


def match_it_companies(title: object, content: object) -> list[ItCompany]:
    """title/content에서 회사 사전 순서대로 매칭된 회사를 반환한다."""
    text = f"{_text_or_empty(title)}\n{_text_or_empty(content)}"
    matches: list[ItCompany] = []
    for company in IT_COMPANIES:
        if any(_contains_alias(text, alias) for alias in company.aliases):
            matches.append(company)
    return matches


def build_company_keyword_values(companies: list[ItCompany]) -> list[str]:
    """회사명과 회사 분류를 `#회사명#분류` 저장 순서에 맞는 flat list로 만든다."""
    values: list[str] = []
    for company in companies:
        values.extend([company.canonical_name, company.company_type])
    return values
