from kag_graph.constants import Domain, Intent
from kag_graph.domain_classifier import DomainClassifier
from kag_graph.intent_classifier import IntentClassifier
from kag_graph.nlp_pipeline import NLPPipeline
from kag_graph.slot_extractor import SlotExtractor
from kag_graph.slot_normalizer import SlotNormalizer
from kag_graph.slot_validator import SlotValidator


class NoFallbackSearch:
    def find_candidate(self, node_label: str, raw_value: str) -> str | None:
        return None


def test_nlp_pipeline_reaches_normalized_validated_slots():
    pipeline = NLPPipeline(
        DomainClassifier(),
        IntentClassifier(),
        SlotExtractor(),
        SlotValidator(),
        SlotNormalizer(NoFallbackSearch()),
    )

    result = pipeline.process("면은 싫은데 중국집 가고 싶어")

    assert result["status"] == "validated"
    assert result["domain"] == Domain.RESTAURANT
    assert result["intent"] == Intent.RESTAURANT_EXCLUSION_SEARCH
    assert len(result["slots"]) == 2


def test_nlp_pipeline_stops_ambiguous_text_as_clarification():
    pipeline = NLPPipeline(
        DomainClassifier(),
        IntentClassifier(),
        SlotExtractor(),
        SlotValidator(),
        SlotNormalizer(NoFallbackSearch()),
    )

    result = pipeline.process("요즘 뭐가 좋아?")

    assert result["status"] == "clarification_required"


class FakeLLMAssist:
    def suggest_domain(self, raw_text: str):
        from kag_graph.llm_assist import LLMAssistResult

        return LLMAssistResult(
            candidates=[{"domain": Domain.RESTAURANT, "confidence": 0.82}],
            confidence=0.82,
            reason="domain candidate",
            needs_clarification=False,
        )

    def suggest_intent(self, raw_text: str, domain: str):
        from kag_graph.llm_assist import LLMAssistResult

        return LLMAssistResult(
            candidates=[{"intent": Intent.RESTAURANT_EXCLUSION_SEARCH, "confidence": 0.86}],
            confidence=0.86,
            reason="intent candidate",
            needs_clarification=False,
        )

    def suggest_slots(self, raw_text: str, domain: str, intent: str):
        from kag_graph.llm_assist import LLMAssistResult

        return LLMAssistResult(candidates=[], confidence=0.0, reason="not used", needs_clarification=True)


class DomainNeedsAssist:
    def classify(self, raw_text: str):
        from kag_graph.constants import Domain
        from kag_graph.models import ClassificationResult

        return ClassificationResult(Domain.UNKNOWN, 0.4, "domain confidence too low", needs_llm_assist=True)


class IntentNeedsAssist:
    def classify(self, raw_text: str, domain: str):
        from kag_graph.constants import Intent
        from kag_graph.models import ClassificationResult

        return ClassificationResult(Intent.CLARIFICATION_REQUIRED, 0.4, "intent confidence too low", needs_llm_assist=True)


def test_nlp_pipeline_can_use_llm_assist_for_low_confidence_domain_and_intent():
    pipeline = NLPPipeline(
        DomainNeedsAssist(),
        IntentNeedsAssist(),
        SlotExtractor(),
        SlotValidator(),
        SlotNormalizer(NoFallbackSearch()),
        llm_assist=FakeLLMAssist(),
    )

    result = pipeline.process("면은 싫은데 중국집 가고 싶어")

    assert result["status"] == "validated"
    assert result["domain"] == Domain.RESTAURANT
    assert result["intent"] == Intent.RESTAURANT_EXCLUSION_SEARCH
