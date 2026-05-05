from dataclasses import dataclass
import re


@dataclass(frozen=True)
class NewsConditionTerm:
    normalized_name: str
    name: str
    kind: str
    identifier: str


@dataclass(frozen=True)
class NewsClassificationResult:
    technologies: list[NewsConditionTerm]
    companies: list[NewsConditionTerm]
    events: list[NewsConditionTerm]
    topics: list[NewsConditionTerm]


TECHNOLOGY_TERMS = (
    NewsConditionTerm("gpt", "GPT", "ai_model", "TECH_GPT"),
    NewsConditionTerm("llm", "LLM", "ai_model", "TECH_LLM"),
    NewsConditionTerm("pytorch", "PyTorch", "framework", "TECH_PYTORCH"),
    NewsConditionTerm("kubernetes", "Kubernetes", "infra", "TECH_KUBERNETES"),
    NewsConditionTerm("react", "React", "frontend", "TECH_REACT"),
    NewsConditionTerm("typescript", "TypeScript", "language", "TECH_TYPESCRIPT"),
)

COMPANY_TERMS = (
    NewsConditionTerm("openai", "OpenAI", "ai", "COMP_OPENAI"),
    NewsConditionTerm("microsoft", "Microsoft", "platform", "COMP_MICROSOFT"),
    NewsConditionTerm("google", "Google", "platform", "COMP_GOOGLE"),
    NewsConditionTerm("apple", "Apple", "platform", "COMP_APPLE"),
    NewsConditionTerm("nvidia", "NVIDIA", "hardware", "COMP_NVIDIA"),
    NewsConditionTerm("anthropic", "Anthropic", "ai", "COMP_ANTHROPIC"),
)

EVENT_TERMS = (
    NewsConditionTerm("update", "업데이트", "release", "EVENT_UPDATE"),
    NewsConditionTerm("release", "출시", "release", "EVENT_RELEASE"),
    NewsConditionTerm("investment", "투자", "market", "EVENT_INVESTMENT"),
    NewsConditionTerm("security_incident", "보안사고", "security", "EVENT_SECURITY_INCIDENT"),
    NewsConditionTerm("regulation", "규제", "policy", "EVENT_REGULATION"),
    NewsConditionTerm("acquisition", "인수", "market", "EVENT_ACQUISITION"),
)

TOPIC_TERMS = (
    NewsConditionTerm("ai", "AI", "technology", "TOPIC_AI"),
    NewsConditionTerm("cloud", "클라우드", "infra", "TOPIC_CLOUD"),
    NewsConditionTerm("security", "보안", "security", "TOPIC_SECURITY"),
    NewsConditionTerm("open_source", "오픈소스", "software", "TOPIC_OPEN_SOURCE"),
    NewsConditionTerm("developer_tool", "개발도구", "software", "TOPIC_DEVELOPER_TOOL"),
)

TERM_ALIASES = {
    "gpt": ("gpt", "chatgpt"),
    "llm": ("llm", "large language model", "large-language-model"),
    "pytorch": ("pytorch", "torch"),
    "kubernetes": ("kubernetes", "k8s"),
    "react": ("react", "reactjs"),
    "typescript": ("typescript", "ts"),
    "openai": ("openai",),
    "microsoft": ("microsoft",),
    "google": ("google",),
    "apple": ("apple",),
    "nvidia": ("nvidia",),
    "anthropic": ("anthropic", "claude"),
    "update": ("update", "updated", "업데이트"),
    "release": ("release", "released", "launch", "launched", "출시", "공개"),
    "investment": ("investment", "invest", "funding", "투자"),
    "security_incident": ("breach", "incident", "attack", "보안사고", "침해"),
    "regulation": ("regulation", "regulatory", "policy", "규제"),
    "acquisition": ("acquisition", "acquire", "merger", "인수", "합병"),
    "ai": ("ai", "artificial intelligence", "인공지능"),
    "cloud": ("cloud", "클라우드"),
    "security": ("security", "보안"),
    "open_source": ("open source", "open-source", "opensource", "오픈소스"),
    "developer_tool": ("developer tool", "devtool", "개발도구", "개발 도구"),
}


class NewsClassifier:
    def classify(self, title: str, content: str) -> NewsClassificationResult:
        text = f"{title} {content}".casefold()
        return NewsClassificationResult(
            technologies=_matched_terms(text, TECHNOLOGY_TERMS),
            companies=_matched_terms(text, COMPANY_TERMS),
            events=_matched_terms(text, EVENT_TERMS),
            topics=_matched_terms(text, TOPIC_TERMS),
        )


def _matched_terms(text: str, terms: tuple[NewsConditionTerm, ...]) -> list[NewsConditionTerm]:
    return [
        term
        for term in terms
        if _contains_alias(text, TERM_ALIASES[term.normalized_name])
    ]


def _contains_alias(text: str, aliases: tuple[str, ...]) -> bool:
    return any(_contains_single_alias(text, alias.casefold()) for alias in aliases)


def _contains_single_alias(text: str, alias: str) -> bool:
    if alias.isascii():
        escaped = re.escape(alias)
        return re.search(rf"(?<![a-z0-9]){escaped}(?![a-z0-9])", text) is not None
    return alias in text
