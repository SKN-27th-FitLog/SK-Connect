from pathlib import Path


def test_kag_seed_does_not_store_price_on_menu_nodes():
    restaurant_seed = Path("queries/seed/restaurant.cypher").read_text(encoding="utf-8")

    assert ".price" not in restaurant_seed
