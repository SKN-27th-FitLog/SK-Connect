from kag_graph.constants import Intent
from kag_graph.models import ExtractedSlot
from kag_graph.slot_validator import SlotValidator


def test_slot_validator_accepts_required_restaurant_exclusion_slots():
    slots = [
        ExtractedSlot("positive_condition", "Menu", "중국집", "중국음식", 0.9, False, True),
        ExtractedSlot("negative_condition", "Ingredient", "면", "면", 0.9, True, True),
    ]

    result = SlotValidator().validate(Intent.RESTAURANT_EXCLUSION_SEARCH, slots)

    assert result.is_valid is True


def test_slot_validator_blocks_missing_required_slot():
    slots = [ExtractedSlot("positive_condition", "Menu", "중국집", "중국음식", 0.9, False, True)]

    result = SlotValidator().validate(Intent.RESTAURANT_EXCLUSION_SEARCH, slots)

    assert result.is_valid is False
    assert result.status == "clarification_required"


def test_slot_validator_blocks_low_confidence_slot():
    slots = [
        ExtractedSlot("positive_condition", "Technology", "GPT", "gpt", 0.6, False, True),
        ExtractedSlot("event", "Event", "업데이트", "업데이트", 0.9, False, True),
    ]

    result = SlotValidator().validate(Intent.NEWS_EVENT_SEARCH, slots)

    assert result.is_valid is False
