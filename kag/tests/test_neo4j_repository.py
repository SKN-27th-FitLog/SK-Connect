from kag_graph.neo4j_repository import path_to_dto


def test_path_to_dto_keeps_empty_path_as_none():
    assert path_to_dto(None) is None
