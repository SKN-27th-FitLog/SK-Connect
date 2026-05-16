from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from kag_graph.extraction.models import ClassifiedKeyword, KeywordCandidate


@dataclass(frozen=True)
class LLMClassificationResult:
    keywords: list[ClassifiedKeyword]
    review_reasons: list[str]


class LLMKeywordClassifier(Protocol):
    def classify(
        self,
        article_id: str,
        candidates: list[KeywordCandidate],
        title: str,
        content: str,
    ) -> list[ClassifiedKeyword]:
        ...


def create_llm_classifier(config: dict[str, str]) -> LLMKeywordClassifier:
    provider = config.get("LLM_PROVIDER", "mock").strip().casefold()
    if provider == "mock":
        from kag_graph.extraction.providers.mock_llm_client import MockLLMKeywordClassifier

        return MockLLMKeywordClassifier()
    if provider == "ollama":
        from kag_graph.extraction.providers.ollama_client import OllamaKeywordClassifier

        return OllamaKeywordClassifier(
            model=config.get("LLM_MODEL", "gemma"),
            timeout_seconds=int(config.get("LLM_TIMEOUT_SECONDS", "20")),
            retry_count=int(config.get("LLM_RETRY_COUNT", "1")),
        )
    raise ValueError(f"unsupported LLM_PROVIDER: {provider}")
