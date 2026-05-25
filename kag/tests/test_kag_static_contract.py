from pathlib import Path


KAG_ROOT = Path(__file__).resolve().parents[1]


def test_kag_seed_does_not_store_price_on_menu_nodes():
    restaurant_seed = (KAG_ROOT / "queries/seed/restaurant.cypher").read_text(encoding="utf-8")

    assert ".price" not in restaurant_seed


def test_news_keyword_constraints_use_canonical_name_for_v2_import():
    constraints = (KAG_ROOT / "queries/schema/constraints.cypher").read_text(encoding="utf-8")

    assert "FOR (n:Technology) REQUIRE n.canonical_name IS UNIQUE" in constraints
    assert "FOR (n:Company) REQUIRE n.canonical_name IS UNIQUE" in constraints
    assert "FOR (n:Event) REQUIRE n.canonical_name IS UNIQUE" in constraints
    assert "FOR (n:Topic) REQUIRE n.canonical_name IS UNIQUE" in constraints
