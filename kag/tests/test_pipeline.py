from kag_graph.constants import Domain, Intent
from kag_graph.pipeline import QueryPipeline


class FailingBuilder:
    def build(self, query_id, domain, intent, slots):
        raise ValueError("missing required slot")


def test_pipeline_returns_clarification_without_query_execution():
    pipeline = QueryPipeline(FailingBuilder())

    result = pipeline.build_or_clarify(
        query_id="Q003",
        domain=Domain.RESTAURANT,
        intent=Intent.RESTAURANT_EXCLUSION_SEARCH,
        slots=[],
    )

    assert result["status"] == "clarification_required"
    assert result["query"] is None
