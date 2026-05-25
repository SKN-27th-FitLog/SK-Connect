from typing import Protocol

from kag_graph.models import ExtractedSlot


class FallbackSearch(Protocol):
    def find_candidate(self, node_label: str, raw_value: str) -> str | None:
        pass


class SlotNormalizationError(ValueError):
    pass


class SlotNormalizer:
    def __init__(self, fallback_search: FallbackSearch):
        self._fallback_search = fallback_search

    def normalize(self, slot: ExtractedSlot) -> ExtractedSlot:
        if slot.normalized_value:
            return slot

        candidate = self._fallback_search.find_candidate(slot.node_label, slot.raw_value)
        if candidate is None:
            raise SlotNormalizationError(slot.raw_value)

        return ExtractedSlot(
            slot_type=slot.slot_type,
            node_label=slot.node_label,
            raw_value=slot.raw_value,
            normalized_value=candidate,
            confidence=0.7,
            is_negative=slot.is_negative,
            is_required=slot.is_required,
        )
