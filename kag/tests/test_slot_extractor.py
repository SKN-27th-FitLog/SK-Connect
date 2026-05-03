from kag_graph.constants import Domain, Intent
from kag_graph.slot_extractor import SlotExtractor


def test_slot_extractor_extracts_restaurant_exclusion_slots():
    slots = SlotExtractor().extract(
        "면은 싫은데 중국집 가고 싶어",
        Domain.RESTAURANT,
        Intent.RESTAURANT_EXCLUSION_SEARCH,
    )

    assert any(slot.node_label == "Menu" and slot.normalized_value == "중국음식" and not slot.is_negative for slot in slots)
    assert any(slot.node_label == "Ingredient" and slot.normalized_value == "면" and slot.is_negative for slot in slots)


def test_slot_extractor_extracts_news_event_slots():
    slots = SlotExtractor().extract("최근 GPT 관련 업데이트 알려줘", Domain.IT_NEWS, Intent.NEWS_EVENT_SEARCH)

    assert any(slot.node_label == "Technology" and slot.normalized_value == "gpt" for slot in slots)
    assert any(slot.node_label == "Event" and slot.normalized_value == "업데이트" for slot in slots)


def test_slot_extractor_extracts_positive_and_negative_tags():
    slots = SlotExtractor().extract(
        "시끄러운 곳 말고 조용한 카페 알려줘",
        Domain.RESTAURANT,
        Intent.RESTAURANT_EXCLUSION_SEARCH,
    )

    assert any(slot.node_label == "Menu" and slot.normalized_value == "카페" for slot in slots)
    assert any(slot.node_label == "Tag" and slot.normalized_value == "조용한" and not slot.is_negative for slot in slots)
    assert any(slot.node_label == "Tag" and slot.normalized_value == "시끄러운" and slot.is_negative for slot in slots)
