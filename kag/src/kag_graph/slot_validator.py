from kag_graph.constants import Intent
from kag_graph.models import ExtractedSlot, ValidationResult


class SlotValidator:
    REQUIRED_SLOTS = {
        Intent.RESTAURANT_EXCLUSION_SEARCH: [("Menu", False), ("Ingredient", True)],
        Intent.NEWS_EVENT_SEARCH: [("Technology", False), ("Event", False)],
        Intent.CONCEPT_BRIDGE_SEARCH: [("Concept", False)],
    }
    ALLOWED_NODE_LABELS = {
        "Area",
        "Menu",
        "Ingredient",
        "Tag",
        "PriceCondition",
        "CapacityCondition",
        "Context",
        "Topic",
        "Technology",
        "Company",
        "Event",
        "Audience",
        "TimeCondition",
        "Concept",
        "NegativeCondition",
        "ComparisonTarget",
    }

    def validate(self, intent: str, slots: list[ExtractedSlot]) -> ValidationResult:
        for slot in slots:
            if slot.node_label not in self.ALLOWED_NODE_LABELS:
                return ValidationResult(False, slots, "clarification_required", f"unsupported slot label: {slot.node_label}")
            if slot.confidence < 0.7:
                return ValidationResult(False, slots, "clarification_required", f"low confidence slot: {slot.raw_value}")

        required_slots = self.REQUIRED_SLOTS.get(intent, [])
        for node_label, is_negative in required_slots:
            if not any(slot.node_label == node_label and slot.is_negative is is_negative for slot in slots):
                return ValidationResult(False, slots, "clarification_required", f"missing required slot: {node_label}")

        return ValidationResult(True, slots, "validated")
