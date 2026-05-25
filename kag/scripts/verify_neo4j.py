from pathlib import Path

from dotenv import load_dotenv
from neo4j import GraphDatabase


ROOT = Path(__file__).resolve().parents[1]


CHECKS = {
    "restaurants_sell_menus": "MATCH (r:Restaurant)-[:SELLS]->(m:Menu) RETURN count(*) AS count",
    "news_mentions_tech": "MATCH (a:NewsArticle)-[:MENTIONS_TECH]->(t:Technology) RETURN count(*) AS count",
    "concept_bridge": "MATCH (:Restaurant)-[:RELATED_TO]->(:Concept)<-[:RELATED_TO]-(:NewsArticle) RETURN count(*) AS count",
    "menu_excludes_ingredient_candidates": """
        MATCH (preferred:Menu {normalized_name: "중국음식"})
        MATCH (excluded:Ingredient {normalized_name: "면"})
        MATCH (restaurant:Restaurant)-[:SELLS]->(menu:Menu)
        WHERE restaurant.is_active = true
          AND menu.normalized_name = preferred.normalized_name
          AND NOT EXISTS { MATCH (menu)-[:CONTAINS]->(excluded) }
        RETURN count(*) AS count
    """,
}


def main() -> None:
    load_dotenv(ROOT / ".env")

    import os

    uri = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
    user = os.environ.get("NEO4J_USER", "neo4j")
    password = os.environ["NEO4J_PASSWORD"]
    database = os.environ.get("NEO4J_DATABASE", "neo4j")

    driver = GraphDatabase.driver(uri, auth=(user, password))
    try:
        with driver.session(database=database) as session:
            for name, cypher in CHECKS.items():
                count = session.run(cypher).single()["count"]
                print(f"{name}: {count}")
    finally:
        driver.close()


if __name__ == "__main__":
    main()
