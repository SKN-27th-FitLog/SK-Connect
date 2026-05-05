import argparse
import os
from pathlib import Path

from dotenv import load_dotenv
from neo4j import GraphDatabase

from kag_graph.hive_importer import (
    collect_current_hive_statements,
    collect_legacy_once_statements,
    load_graph_statements,
)


ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = ROOT.parent
DEFAULT_MEAL_ROOT = PROJECT_ROOT / "etl/meal/_temp_lake"
DEFAULT_IT_NEWS_ROOT = PROJECT_ROOT / "etl/it_news"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import Hive ETL success outputs into KAG Neo4j.")
    parser.add_argument(
        "--mode",
        choices=["legacy-once", "current-hive"],
        required=True,
        help="legacy-once는 기존 어긋난 meal 경로를, current-hive는 현재 meal process=cleansing 경로를 읽습니다.",
    )
    parser.add_argument("--meal-root", type=Path, default=DEFAULT_MEAL_ROOT)
    parser.add_argument("--it-news-root", type=Path, default=DEFAULT_IT_NEWS_ROOT)
    parser.add_argument("--dry-run", action="store_true", help="Neo4j에 쓰지 않고 statement 수만 확인합니다.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    load_dotenv(ROOT / ".env")

    if args.mode == "legacy-once":
        statements = collect_legacy_once_statements(args.meal_root, args.it_news_root)
    else:
        statements = collect_current_hive_statements(args.meal_root, args.it_news_root)

    print(f"mode={args.mode}")
    print(f"meal_root={args.meal_root}")
    print(f"it_news_root={args.it_news_root}")
    print(f"statements={len(statements)}")

    if args.dry_run:
        return

    uri = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
    user = os.environ.get("NEO4J_USER", "neo4j")
    password = os.environ["NEO4J_PASSWORD"]
    database = os.environ.get("NEO4J_DATABASE", "neo4j")

    driver = GraphDatabase.driver(uri, auth=(user, password))
    try:
        loaded = load_graph_statements(driver, database, statements)
    finally:
        driver.close()

    print(f"loaded={len(loaded)}")


if __name__ == "__main__":
    main()
