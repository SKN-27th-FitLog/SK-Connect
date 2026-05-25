import json
from pathlib import Path

from kag_graph.hive_importer import build_recipe_ingredient_map


def test_build_recipe_ingredient_map_uses_first_non_empty_recipe_per_keyword(tmp_path: Path):
    recipe_file = tmp_path / "recipe_collection.jsonl"
    records = [
        {
            "recipe_search_keyword": "menu-a",
            "recipe_url": "https://www.10000recipe.com/recipe/empty",
            "ingredients": [],
        },
        {
            "recipe_search_keyword": "menu-a",
            "recipe_url": "https://www.10000recipe.com/recipe/first",
            "ingredients": [
                {"ingredient_name": "ingredient-1"},
                {"ingredient_name": "ingredient-2"},
            ],
        },
        {
            "recipe_search_keyword": "menu-a",
            "recipe_url": "https://www.10000recipe.com/recipe/second",
            "ingredients": [
                {"ingredient_name": "ingredient-3"},
            ],
        },
    ]
    recipe_file.write_text(
        "\n".join(json.dumps(record, ensure_ascii=False) for record in records) + "\n",
        encoding="utf-8",
    )

    result = build_recipe_ingredient_map([recipe_file])

    assert result["menu-a"] == [
        {
            "ingredient_name": "ingredient-1",
            "recipe_url": "https://www.10000recipe.com/recipe/first",
        },
        {
            "ingredient_name": "ingredient-2",
            "recipe_url": "https://www.10000recipe.com/recipe/first",
        },
    ]
