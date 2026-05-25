from kag_graph.models import ExtractedSlot


class QueryPipeline:
    def __init__(self, query_builder):
        self._query_builder = query_builder

    def build_or_clarify(
        self,
        query_id: str,
        domain: str,
        intent: str,
        slots: list[ExtractedSlot],
    ) -> dict[str, object]:
        try:
            query = self._query_builder.build(query_id, domain, intent, slots)
            return {"status": "query_built", "query": query, "message": None}
        except ValueError as exc:
            return {
                "status": "clarification_required",
                "query": None,
                "message": str(exc),
            }
