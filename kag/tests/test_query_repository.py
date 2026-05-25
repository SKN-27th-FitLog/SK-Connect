from pathlib import Path

from kag_graph.query_repository import QueryRepository


def test_query_repository_loads_template_by_name():
    query_file = Path("tests/fixtures/sample.cypher")

    repository = QueryRepository({"sample": query_file})

    assert repository.get("sample") == "MATCH (n) RETURN n;"
