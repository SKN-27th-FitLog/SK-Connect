import pytest

from kag_graph.constants import Domain, Intent, TemplateName
from kag_graph.models import ExtractedSlot
from kag_graph.query_builder import GraphQueryBuilder, UnsupportedQueryError


class FakeQueryRepository:
    def get(self, template_name: str) -> str:
        return f"-- {template_name}"


def test_extracted_slot_uses_normalized_value_for_query_value():
    slot = ExtractedSlot(
        slot_type="positive_condition",
        node_label="Menu",
        raw_value="중국집",
        normalized_value="중국음식",
        confidence=0.95,
        is_negative=False,
        is_required=True,
    )

    assert slot.query_value == "중국음식"


def test_constants_include_priority_templates():
    assert Domain.RESTAURANT == "restaurant"
    assert Domain.MIXED == "mixed"
    assert Intent.RESTAURANT_EXCLUSION_SEARCH == "restaurant_exclusion_search"
    assert TemplateName.RESTAURANT_MENU_EXCLUDE_INGREDIENT == "restaurant_menu_exclude_ingredient"
    assert TemplateName.NEWS_AUDIENCE_FILTER == "news_audience_filter"


def test_query_builder_selects_restaurant_exclusion_template():
    slots = [
        ExtractedSlot("positive_condition", "Menu", "중국집", "중국음식", 0.95, False, True),
        ExtractedSlot("negative_condition", "Ingredient", "면", "면", 0.95, True, True),
    ]
    builder = GraphQueryBuilder(FakeQueryRepository())

    result = builder.build(
        query_id="Q001",
        domain=Domain.RESTAURANT,
        intent=Intent.RESTAURANT_EXCLUSION_SEARCH,
        slots=slots,
    )

    assert result.template_name == TemplateName.RESTAURANT_MENU_EXCLUDE_INGREDIENT
    assert result.params["menu_name"] == "중국음식"
    assert result.params["excluded_ingredient"] == "면"
    assert result.params["exclude_strength"] == "hard"


def test_query_builder_selects_news_event_template():
    slots = [
        ExtractedSlot("positive_condition", "Technology", "GPT", "gpt", 0.95, False, True),
        ExtractedSlot("event", "Event", "업데이트", "업데이트", 0.95, False, True),
    ]
    builder = GraphQueryBuilder(FakeQueryRepository())

    result = builder.build("Q002", Domain.IT_NEWS, Intent.NEWS_EVENT_SEARCH, slots)

    assert result.template_name == TemplateName.NEWS_TECH_EVENT_SEARCH
    assert result.params["technology_name"] == "gpt"
    assert result.params["event_name"] == "업데이트"


def test_query_builder_rejects_templates_outside_mvp_scope():
    builder = GraphQueryBuilder(FakeQueryRepository())

    with pytest.raises(UnsupportedQueryError):
        builder.build("Q003", Domain.RESTAURANT, Intent.RESTAURANT_RECOMMENDATION, [])
