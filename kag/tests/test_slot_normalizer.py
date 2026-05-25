from kag_graph.models import ExtractedSlot
from kag_graph.slot_normalizer import SlotNormalizer


class FakeFallbackSearch:
    def find_candidate(self, node_label: str, raw_value: str) -> str | None:
        if node_label == "Menu" and raw_value == "중국집":
            return "중국음식"
        return None


def test_slot_normalizer_uses_fulltext_candidate_before_query_builder():
    normalizer = SlotNormalizer(FakeFallbackSearch())
    slot = ExtractedSlot("positive_condition", "Menu", "중국집", "", 0.4, False, True)

    normalized = normalizer.normalize(slot)

    assert normalized.normalized_value == "중국음식"
    assert normalized.confidence == 0.7
