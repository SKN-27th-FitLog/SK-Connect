from kag_graph.constants import Domain, Intent, TemplateName
from kag_graph.models import ExtractedSlot, QueryBuildResult
from kag_graph.query_repository import QueryRepository


class UnsupportedQueryError(ValueError):
    pass


class MissingRequiredSlotError(ValueError):
    pass


class GraphQueryBuilder:
    def __init__(self, query_repository: QueryRepository):
        self._query_repository = query_repository
        self._template_map = {
            (Domain.RESTAURANT, Intent.RESTAURANT_EXCLUSION_SEARCH): TemplateName.RESTAURANT_MENU_EXCLUDE_INGREDIENT,
            (Domain.IT_NEWS, Intent.NEWS_EVENT_SEARCH): TemplateName.NEWS_TECH_EVENT_SEARCH,
        }

    def build(
        self,
        query_id: str,
        domain: str,
        intent: str,
        slots: list[ExtractedSlot],
    ) -> QueryBuildResult:
        template_name = self._select_template(domain, intent)
        params = self._build_params(query_id, template_name, slots)
        query_text = self._query_repository.get(template_name)

        return QueryBuildResult(
            template_name=template_name,
            query_text=query_text,
            params=params,
            expected_path_pattern=template_name,
        )

    def _select_template(self, domain: str, intent: str) -> str:
        template_name = self._template_map.get((domain, intent))
        if template_name is None:
            raise UnsupportedQueryError(f"{domain}:{intent}")

        return template_name

    def _build_params(
        self,
        query_id: str,
        template_name: str,
        slots: list[ExtractedSlot],
    ) -> dict[str, object]:
        if template_name == TemplateName.RESTAURANT_MENU_EXCLUDE_INGREDIENT:
            menu = self._required_slot(slots, "Menu", is_negative=False)
            ingredient = self._required_slot(slots, "Ingredient", is_negative=True)
            return {
                "query_id": query_id,
                "menu_name": menu.query_value,
                "excluded_ingredient": ingredient.query_value,
                "exclude_strength": "hard",
                "limit": 5,
            }

        if template_name == TemplateName.NEWS_TECH_EVENT_SEARCH:
            technology = self._required_slot(slots, "Technology", is_negative=False)
            event = self._required_slot(slots, "Event", is_negative=False)
            return {
                "query_id": query_id,
                "technology_name": technology.query_value,
                "event_name": event.query_value,
                "limit": 5,
            }

        raise UnsupportedQueryError(f"Parameter builder is not implemented for {template_name}")

    def _required_slot(
        self,
        slots: list[ExtractedSlot],
        node_label: str,
        is_negative: bool,
    ) -> ExtractedSlot:
        for slot in slots:
            if slot.node_label == node_label and slot.is_negative is is_negative:
                return slot

        raise MissingRequiredSlotError(node_label)
