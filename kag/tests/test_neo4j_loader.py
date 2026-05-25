from pathlib import Path

from kag_graph.neo4j_loader import CypherFile, load_cypher_files


class FakeSession:
    def __init__(self):
        self.executed = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def run(self, cypher: str):
        self.executed.append(cypher)


class FakeDriver:
    def __init__(self):
        self.session_obj = FakeSession()
        self.database = None

    def session(self, database: str):
        self.database = database
        return self.session_obj


def test_load_cypher_files_runs_files_in_order():
    first = "tests/fixtures/loader_001.cypher"
    second = "tests/fixtures/loader_002.cypher"
    driver = FakeDriver()

    loaded = load_cypher_files(
        driver,
        database="neo4j",
        files=[CypherFile("first", Path(first)), CypherFile("second", Path(second))],
    )

    assert loaded == ["first", "second"]
    assert driver.database == "neo4j"
    assert driver.session_obj.executed == ["MATCH (n) RETURN n;", "MATCH (m) RETURN m;"]


def test_load_cypher_files_splits_multiple_statements_per_file():
    driver = FakeDriver()

    loaded = load_cypher_files(
        driver,
        database="neo4j",
        files=[CypherFile("multi", Path("tests/fixtures/loader_multi.cypher"))],
    )

    assert loaded == ["multi"]
    assert driver.session_obj.executed == [
        "MATCH (n) RETURN n;",
        "MATCH (m) RETURN m;",
    ]
