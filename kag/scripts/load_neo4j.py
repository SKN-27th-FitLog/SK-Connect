from pathlib import Path

from dotenv import load_dotenv
from neo4j import GraphDatabase

from kag_graph.neo4j_loader import CypherFile, load_cypher_files


ROOT = Path(__file__).resolve().parents[1]


def cypher_files() -> list[CypherFile]:
    return [
        CypherFile("constraints", ROOT / "queries/schema/constraints.cypher"),
        CypherFile("fulltext_indexes", ROOT / "queries/schema/fulltext_indexes.cypher"),
        CypherFile("reset", ROOT / "queries/seed/reset.cypher"),
        CypherFile("restaurant_seed", ROOT / "queries/seed/restaurant.cypher"),
        CypherFile("news_seed", ROOT / "queries/seed/news.cypher"),
        CypherFile("common_seed", ROOT / "queries/seed/common.cypher"),
    ]


def main() -> None:
    load_dotenv(ROOT / ".env")

    import os

    uri = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
    user = os.environ.get("NEO4J_USER", "neo4j")
    password = os.environ["NEO4J_PASSWORD"]
    database = os.environ.get("NEO4J_DATABASE", "neo4j")

    driver = GraphDatabase.driver(uri, auth=(user, password))
    try:
        loaded = load_cypher_files(driver, database, cypher_files())
    finally:
        driver.close()

    for name in loaded:
        print(f"loaded: {name}")


if __name__ == "__main__":
    main()
