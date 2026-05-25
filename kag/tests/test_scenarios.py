from kag_graph.constants import Domain, Intent, TemplateName
from kag_graph.models import ExtractedSlot
from kag_graph.query_builder import GraphQueryBuilder


class FakeQueryRepository:
    def get(self, template_name: str) -> str:
        return f"-- {template_name}"


def test_r_03_menu_excludes_ingredient_template():
    builder = GraphQueryBuilder(FakeQueryRepository())
    slots = [
        ExtractedSlot("positive_condition", "Menu", "중국집", "중국음식", 0.95, False, True),
        ExtractedSlot("negative_condition", "Ingredient", "면", "면", 0.95, True, True),
    ]

    result = builder.build("Q001", Domain.RESTAURANT, Intent.RESTAURANT_EXCLUSION_SEARCH, slots)

    assert result.template_name == TemplateName.RESTAURANT_MENU_EXCLUDE_INGREDIENT
    assert result.params["menu_name"] == "중국음식"
    assert result.params["excluded_ingredient"] == "면"


def test_n_02_technology_event_template():
    builder = GraphQueryBuilder(FakeQueryRepository())
    slots = [
        ExtractedSlot("positive_condition", "Technology", "GPT", "gpt", 0.95, False, True),
        ExtractedSlot("event", "Event", "업데이트", "업데이트", 0.95, False, True),
    ]

    result = builder.build("Q002", Domain.IT_NEWS, Intent.NEWS_EVENT_SEARCH, slots)

    assert result.template_name == TemplateName.NEWS_TECH_EVENT_SEARCH
    assert result.params["technology_name"] == "gpt"
    assert result.params["event_name"] == "업데이트"
