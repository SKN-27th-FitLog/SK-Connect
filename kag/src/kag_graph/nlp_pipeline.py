from kag_graph.models import ExtractedSlot


class NLPPipeline:
    def __init__(self, domain_classifier, intent_classifier, slot_extractor, slot_validator, slot_normalizer, llm_assist=None):
        self._domain_classifier = domain_classifier
        self._intent_classifier = intent_classifier
        self._slot_extractor = slot_extractor
        self._slot_validator = slot_validator
        self._slot_normalizer = slot_normalizer
        self._llm_assist = llm_assist

    def process(self, raw_text: str) -> dict[str, object]:
        domain_result = self._domain_classifier.classify(raw_text)
        if domain_result.needs_llm_assist:
            domain_result = self._domain_from_assist(raw_text, domain_result)

        if domain_result.value == "unknown":
            return {"status": "clarification_required", "message": domain_result.reason}

        intent_result = self._intent_classifier.classify(raw_text, domain_result.value)
        if intent_result.needs_llm_assist:
            intent_result = self._intent_from_assist(raw_text, domain_result.value, intent_result)

        if intent_result.value == "clarification_required":
            return {"status": "clarification_required", "message": intent_result.reason}

        slots = self._slot_extractor.extract(raw_text, domain_result.value, intent_result.value)
        if not slots and self._llm_assist is not None:
            assist_result = self._llm_assist.suggest_slots(raw_text, domain_result.value, intent_result.value)
            if assist_result.needs_clarification:
                return {"status": "clarification_required", "message": assist_result.reason}
            slots = self._slots_from_candidates(assist_result.candidates)

        normalized_slots = [self._slot_normalizer.normalize(slot) for slot in slots]
        validation = self._slot_validator.validate(intent_result.value, normalized_slots)
        if not validation.is_valid:
            return {"status": "clarification_required", "message": validation.message}

        return {
            "status": "validated",
            "domain": domain_result.value,
            "intent": intent_result.value,
            "slots": validation.slots,
        }

    def _slots_from_candidates(self, candidates: list[dict[str, object]]) -> list[ExtractedSlot]:
        return [
            ExtractedSlot(
                slot_type=str(candidate.get("slot_type", "positive_condition")),
                node_label=str(candidate["node_label"]),
                raw_value=str(candidate["raw_value"]),
                normalized_value=str(candidate.get("candidate_value", "")),
                confidence=float(candidate["confidence"]),
                is_negative=bool(candidate.get("is_negative", False)),
                is_required=True,
            )
            for candidate in candidates
        ]

    def _domain_from_assist(self, raw_text: str, fallback_result):
        if self._llm_assist is None:
            return fallback_result

        assist_result = self._llm_assist.suggest_domain(raw_text)
        if assist_result.needs_clarification or not assist_result.candidates:
            return fallback_result

        candidate = max(assist_result.candidates, key=lambda item: float(item["confidence"]))
        return type(fallback_result)(
            value=str(candidate["domain"]),
            confidence=float(candidate["confidence"]),
            reason=assist_result.reason,
            needs_llm_assist=False,
        )

    def _intent_from_assist(self, raw_text: str, domain: str, fallback_result):
        if self._llm_assist is None:
            return fallback_result

        assist_result = self._llm_assist.suggest_intent(raw_text, domain)
        if assist_result.needs_clarification or not assist_result.candidates:
            return fallback_result

        candidate = max(assist_result.candidates, key=lambda item: float(item["confidence"]))
        return type(fallback_result)(
            value=str(candidate["intent"]),
            confidence=float(candidate["confidence"]),
            reason=assist_result.reason,
            needs_llm_assist=False,
        )
