from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class LLMAssistResult:
    candidates: list[dict[str, object]]
    confidence: float
    reason: str
    needs_clarification: bool


class LLMAssist(Protocol):
    def suggest_domain(self, raw_text: str) -> LLMAssistResult:
        pass

    def suggest_intent(self, raw_text: str, domain: str) -> LLMAssistResult:
        pass

    def suggest_slots(self, raw_text: str, domain: str, intent: str) -> LLMAssistResult:
        pass
