import csv
import json
from pathlib import Path

from kag_graph.hive_importer import (
    build_it_news_article_statements,
    build_address_name_map,
    build_meal_restaurant_statements,
    build_menu_ingredient_map,
    build_recipe_ingredient_map,
    collect_current_hive_statements,
    collect_legacy_once_statements,
    find_it_news_cleaning_success_files,
    find_meal_legacy_cleansing_success_files,
    find_meal_process_cleansing_success_files,
    find_meal_recipe_success_files,
    load_graph_statements,
)


SAMPLE_RESTAURANT_URL = "https://example.com/store"


def test_find_it_news_cleaning_success_files_keeps_cleaning_process(tmp_path: Path):
    root = tmp_path / "it"
    success_file = root / "process=cleaning/category_cd=IC02/year=2026/month=05/day=05/status=success/it_news_132516.csv"
    success_file.parent.mkdir(parents=True)
    success_file.write_text("title\nsample\n", encoding="utf-8")
    ignored = root / "process=cleansing/category_cd=IC02/year=2026/month=05/day=05/status=success/wrong.csv"
    ignored.parent.mkdir(parents=True)
    ignored.write_text("title\nwrong\n", encoding="utf-8")

    files = find_it_news_cleaning_success_files(root)

    assert files == [success_file]


def test_find_meal_legacy_cleansing_success_files_uses_crawling_partition(tmp_path: Path):
    root = tmp_path / "meal"
    success_file = root / "crawling=cleansing/service=SC01/year=2026/month=05/day=05/stage=validation_normalization/batch_id=20260505_SC01_001/status=success/260505083633_att1.jsonl"
    success_file.parent.mkdir(parents=True)
    success_file.write_text("{}\n", encoding="utf-8")
    ignored = root / "process=cleaning/category_cd=CA01/shop_cd=SC01/year=2026/month=05/day=05/status=success/validation_normalization_20260505_SC01_001_260505083633_att1.jsonl"
    ignored.parent.mkdir(parents=True)
    ignored.write_text("{}\n", encoding="utf-8")

    files = find_meal_legacy_cleansing_success_files(root)

    assert files == [success_file]


def test_find_meal_process_cleansing_success_files_uses_current_hive_partition(tmp_path: Path):
    root = tmp_path / "meal"
    success_file = root / "process=cleaning/category_cd=CA01/shop_cd=SC01/year=2026/month=05/day=05/status=success/validation_normalization_20260505_SC01_001_260505083633_att1.jsonl"
    success_file.parent.mkdir(parents=True)
    success_file.write_text("{}\n", encoding="utf-8")
    ignored = root / "crawling=cleansing/service=SC01/year=2026/month=05/day=05/stage=validation_normalization/batch_id=20260505_SC01_001/status=success/260505083633_att1.jsonl"
    ignored.parent.mkdir(parents=True)
    ignored.write_text("{}\n", encoding="utf-8")

    files = find_meal_process_cleansing_success_files(root)

    assert files == [success_file]


def test_build_it_news_article_statements_maps_cleaning_csv_to_news_article(tmp_path: Path):
    csv_file = tmp_path / "it_news.csv"
    with csv_file.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=["title", "content", "thread", "article_url", "created_at", "author", "category_cd", "_page_service"],
        )
        writer.writeheader()
        writer.writerow(
            {
                "title": "Personal essay about development habits",
                "content": "No configured graph condition appears here.",
                "thread": "geeknews_1",
                "article_url": "https://example.com/a",
                "created_at": "2026-05-05 13:25:16",
                "author": "tester",
                "category_cd": "IC02",
                "_page_service": "geeknews",
            }
        )

    statements = build_it_news_article_statements(csv_file)

    assert len(statements) == 1
    assert statements[0].params["article_id"] == "geeknews_1"
    assert statements[0].params["title"] == "Personal essay about development habits"
    assert "MERGE (article:NewsArticle" in statements[0].cypher


def test_build_it_news_article_statements_maps_news_conditions_to_relationships(tmp_path: Path):
    csv_file = tmp_path / "it_news.csv"
    with csv_file.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=["title", "content", "thread", "article_url", "created_at", "author", "category_cd", "_page_service"],
        )
        writer.writeheader()
        writer.writerow(
            {
                "title": "OpenAI GPT update improves cloud security",
                "content": "Microsoft also mentioned Kubernetes support.",
                "thread": "geeknews_1",
                "article_url": "https://example.com/a",
                "created_at": "2026-05-05 13:25:16",
                "author": "tester",
                "category_cd": "IC02",
                "_page_service": "geeknews",
            }
        )

    statements = build_it_news_article_statements(csv_file)

    assert [statement.name for statement in statements] == [
        "news_article:geeknews_1",
        "news_technology:geeknews_1:gpt",
        "news_technology:geeknews_1:kubernetes",
        "news_company:geeknews_1:openai",
        "news_company:geeknews_1:microsoft",
        "news_event:geeknews_1:update",
        "news_topic:geeknews_1:cloud",
        "news_topic:geeknews_1:security",
    ]
    assert statements[1].params == {
        "article_id": "geeknews_1",
        "normalized_name": "gpt",
        "name": "GPT",
        "kind": "ai_model",
        "identifier": "TECH_GPT",
    }
    assert "MERGE (technology:Technology" in statements[1].cypher


def test_build_meal_restaurant_statements_maps_store_menu_and_keyword_tags(tmp_path: Path):
    jsonl_file = tmp_path / "meal.jsonl"
    record = {
        "store": {
            "entity_id": "LA143",
            "name": "동화고옥 선릉점",
            "address_detail": "서울 강남구",
            "rating": 4.8,
            "canonical_url": "https://example.com/store",
        },
        "menus": [{"name": "불고기", "price": 39000}],
        "reviews": [{"keywords": ["조용한", "깔끔한"]}],
    }
    jsonl_file.write_text(json.dumps(record, ensure_ascii=False) + "\n", encoding="utf-8")

    statements = build_meal_restaurant_statements(jsonl_file)

    assert [statement.name for statement in statements] == [
        f"restaurant:{SAMPLE_RESTAURANT_URL}",
        f"restaurant_menu:{SAMPLE_RESTAURANT_URL}:불고기",
        f"restaurant_tag:{SAMPLE_RESTAURANT_URL}:조용한",
        f"restaurant_tag:{SAMPLE_RESTAURANT_URL}:깔끔한",
    ]
    assert statements[0].params["restaurant_id"] == SAMPLE_RESTAURANT_URL
    assert statements[1].params["normalized_name"] == "불고기"
    assert statements[1].params["raw_menu_name"] == "불고기"
    assert statements[1].params["price"] == 39000
    assert statements[2].params["tag_name"] == "조용한"


def test_build_meal_restaurant_statements_uses_url_as_restaurant_id(tmp_path: Path):
    jsonl_file = tmp_path / "meal.jsonl"
    _write_meal_jsonl(
        jsonl_file,
        address_cd="LA143",
        canonical_url="https://www.diningcode.com/profile.php?rid=abc123",
    )

    statements = build_meal_restaurant_statements(jsonl_file)

    assert statements[0].name == "restaurant:https://www.diningcode.com/profile.php?rid=abc123"
    assert statements[0].params["restaurant_id"] == "https://www.diningcode.com/profile.php?rid=abc123"
    assert statements[1].params["restaurant_id"] == "https://www.diningcode.com/profile.php?rid=abc123"
    assert statements[2].params["restaurant_id"] == "https://www.diningcode.com/profile.php?rid=abc123"


def test_build_meal_restaurant_statements_uses_name_address_without_url(tmp_path: Path):
    jsonl_file = tmp_path / "meal.jsonl"
    _write_meal_jsonl(
        jsonl_file,
        canonical_url="",
        address_cd="LA143",
    )

    statements = build_meal_restaurant_statements(jsonl_file)

    assert statements[0].params["restaurant_id"] == "동화고옥 선릉점|서울 강남구"


def test_build_meal_restaurant_statements_maps_address_code_to_area_relationship(tmp_path: Path):
    jsonl_file = tmp_path / "meal.jsonl"
    code_table = tmp_path / "codeT.csv"
    _write_meal_jsonl(jsonl_file, address_cd="LA143")
    _write_address_code_csv(code_table)

    statements = build_meal_restaurant_statements(
        jsonl_file,
        address_name_map=build_address_name_map(code_table),
    )

    assert [statement.name for statement in statements][:2] == [
        f"restaurant:{SAMPLE_RESTAURANT_URL}",
        f"restaurant_area:{SAMPLE_RESTAURANT_URL}:LA143",
    ]
    assert statements[1].params == {
        "restaurant_id": SAMPLE_RESTAURANT_URL,
        "address_cd": "LA143",
        "address_name": "서울특별시 강남구",
    }
    assert "MERGE (area:Area" in statements[1].cypher
    assert "LOCATED_IN" in statements[1].cypher


def test_build_address_name_map_reads_utf8_sig_code_table(tmp_path: Path):
    code_table = tmp_path / "codeT.csv"
    code_table.write_text(
        "\ufeffcd,name,cd_info,cd_upper\nLA143,서울특별시 강남구,주소,LA00\n",
        encoding="utf-8",
    )

    address_name_map = build_address_name_map(code_table)

    assert address_name_map["LA143"] == "서울특별시 강남구"


def test_build_meal_restaurant_statements_skips_area_without_address_code(tmp_path: Path):
    jsonl_file = tmp_path / "meal.jsonl"
    record = {
        "store": {
            "entity_id": "store-1",
            "name": "주소없는식당",
            "rating": 4.8,
            "canonical_url": "https://example.com/store",
        },
        "menus": [],
        "reviews": [],
    }
    jsonl_file.write_text(json.dumps(record, ensure_ascii=False) + "\n", encoding="utf-8")

    statements = build_meal_restaurant_statements(jsonl_file)

    assert [statement.name for statement in statements] == [f"restaurant:{SAMPLE_RESTAURANT_URL}"]


def test_collect_legacy_once_statements_reads_it_news_cleaning_and_meal_legacy(tmp_path: Path):
    it_root = tmp_path / "it"
    meal_root = tmp_path / "meal"
    news_file = it_root / "process=cleaning/category_cd=IC02/year=2026/month=05/day=05/status=success/it_news.csv"
    news_file.parent.mkdir(parents=True)
    _write_news_csv(news_file)
    meal_file = meal_root / "crawling=cleansing/service=SC01/year=2026/month=05/day=05/stage=validation_normalization/batch_id=20260505_SC01_001/status=success/meal.jsonl"
    meal_file.parent.mkdir(parents=True)
    _write_meal_jsonl(meal_file)

    statements = collect_legacy_once_statements(meal_root=meal_root, it_news_root=it_root)

    assert [statement.name for statement in statements] == [
        f"restaurant:{SAMPLE_RESTAURANT_URL}",
        f"restaurant_menu:{SAMPLE_RESTAURANT_URL}:불고기",
        "menu_ingredient:불고기:소고기",
        f"restaurant_tag:{SAMPLE_RESTAURANT_URL}:조용한",
        "news_article:geeknews_1",
    ]


def test_collect_current_hive_statements_reads_it_news_cleaning_and_meal_process(tmp_path: Path):
    it_root = tmp_path / "it"
    meal_root = tmp_path / "meal"
    news_file = it_root / "process=cleaning/category_cd=IC02/year=2026/month=05/day=05/status=success/it_news.csv"
    news_file.parent.mkdir(parents=True)
    _write_news_csv(news_file)
    meal_file = meal_root / "process=cleaning/category_cd=CA01/shop_cd=SC01/year=2026/month=05/day=05/status=success/validation_normalization_20260505_SC01_001_260505083633_att1.jsonl"
    meal_file.parent.mkdir(parents=True)
    _write_meal_jsonl(meal_file)

    statements = collect_current_hive_statements(meal_root=meal_root, it_news_root=it_root)

    assert [statement.name for statement in statements] == [
        f"restaurant:{SAMPLE_RESTAURANT_URL}",
        f"restaurant_menu:{SAMPLE_RESTAURANT_URL}:불고기",
        "menu_ingredient:불고기:소고기",
        f"restaurant_tag:{SAMPLE_RESTAURANT_URL}:조용한",
        "news_article:geeknews_1",
    ]


def test_collect_legacy_once_statements_deduplicates_repeated_success_files(tmp_path: Path):
    it_root = tmp_path / "it"
    meal_root = tmp_path / "meal"
    news_file = it_root / "process=cleaning/category_cd=IC02/year=2026/month=05/day=05/status=success/it_news.csv"
    news_file.parent.mkdir(parents=True)
    _write_news_csv(news_file)
    first_meal_file = meal_root / "crawling=cleansing/service=SC01/year=2026/month=05/day=05/stage=validation_normalization/batch_id=20260505_SC01_001/status=success/260505083231.jsonl"
    second_meal_file = meal_root / "crawling=cleansing/service=SC01/year=2026/month=05/day=05/stage=validation_normalization/batch_id=20260505_SC01_001/status=success/260505083633_att1.jsonl"
    first_meal_file.parent.mkdir(parents=True)
    _write_meal_jsonl(first_meal_file)
    _write_meal_jsonl(second_meal_file)

    statements = collect_legacy_once_statements(meal_root=meal_root, it_news_root=it_root)

    assert [statement.name for statement in statements] == [
        f"restaurant:{SAMPLE_RESTAURANT_URL}",
        f"restaurant_menu:{SAMPLE_RESTAURANT_URL}:불고기",
        "menu_ingredient:불고기:소고기",
        f"restaurant_tag:{SAMPLE_RESTAURANT_URL}:조용한",
        "news_article:geeknews_1",
    ]


def test_build_meal_restaurant_statements_creates_contains_for_mapped_menu(tmp_path: Path):
    jsonl_file = tmp_path / "meal.jsonl"
    record = {
        "store": {
            "entity_id": "store-noodle",
            "name": "짜장면집",
            "address_detail": "서울 강남구",
            "rating": 4.0,
            "canonical_url": "https://example.com/noodle",
        },
        "menus": [{"name": "짜장면", "price": 8000}],
        "reviews": [],
    }
    jsonl_file.write_text(json.dumps(record, ensure_ascii=False) + "\n", encoding="utf-8")

    statements = build_meal_restaurant_statements(
        jsonl_file,
        menu_ingredient_map={"짜장면": ("면",)},
    )

    names = [s.name for s in statements]
    assert "restaurant_menu:https://example.com/noodle:짜장면" in names
    assert "menu_ingredient:짜장면:면" in names

    contains_stmt = next(s for s in statements if s.name == "menu_ingredient:짜장면:면")
    assert contains_stmt.params == {
        "menu_name": "짜장면",
        "ingredient_name": "면",
        "ingredient_source": "CSV_FALLBACK",
        "source_url": "",
        "ingredient_confidence": 0.5,
        "fallback_used": True,
    }
    assert "CONTAINS" in contains_stmt.cypher


def test_build_meal_restaurant_statements_keeps_store_menu_data_on_sells_relationship(tmp_path: Path):
    jsonl_file = tmp_path / "meal.jsonl"
    record = {
        "store": {
            "entity_id": "store-menu-normalized",
            "name": "제육집",
            "address_detail": "서울 강남구",
            "rating": 4.0,
            "canonical_url": "https://example.com/pork",
        },
        "menus": [
            {
                "name": "직화 제육 정식 2인",
                "price": 12000,
                "raw_menu_name": "직화 제육 정식 2인",
                "display_menu_name": "직화 제육 정식 2인",
                "normalized_name": "제육볶음",
                "canonical_name": "제육볶음",
                "recipe_search_keyword": "제육볶음",
                "menu_confidence": 0.94,
                "menu_normalization_status": "NORMALIZED",
                "normalization_method": "RULE_SIMILARITY",
            }
        ],
        "reviews": [],
    }
    jsonl_file.write_text(json.dumps(record, ensure_ascii=False) + "\n", encoding="utf-8")

    statements = build_meal_restaurant_statements(jsonl_file)

    menu_stmt = next(s for s in statements if s.name == "restaurant_menu:https://example.com/pork:직화 제육 정식 2인")
    assert "MERGE (menu:Menu {normalized_name: $normalized_name})" in menu_stmt.cypher
    assert "menu.price" not in menu_stmt.cypher
    assert "MERGE (restaurant)-[s:SELLS]->(menu)" in menu_stmt.cypher
    assert "s.raw_menu_name" in menu_stmt.cypher
    assert menu_stmt.params == {
        "restaurant_id": "https://example.com/pork",
        "raw_menu_name": "직화 제육 정식 2인",
        "display_menu_name": "직화 제육 정식 2인",
        "normalized_name": "제육볶음",
        "canonical_name": "제육볶음",
        "recipe_search_keyword": "제육볶음",
        "menu_confidence": 0.94,
        "menu_normalization_status": "NORMALIZED",
        "normalization_method": "RULE_SIMILARITY",
        "price": 12000,
    }


def test_build_meal_restaurant_statements_sets_contains_edge_source_metadata(tmp_path: Path):
    jsonl_file = tmp_path / "meal.jsonl"
    record = {
        "store": {
            "entity_id": "store-noodle",
            "name": "짜장면집",
            "address_detail": "서울 강남구",
            "rating": 4.0,
            "canonical_url": "https://example.com/noodle",
        },
        "menus": [{"name": "짜장면", "price": 8000}],
        "reviews": [],
    }
    jsonl_file.write_text(json.dumps(record, ensure_ascii=False) + "\n", encoding="utf-8")

    statements = build_meal_restaurant_statements(
        jsonl_file,
        menu_ingredient_map={"짜장면": ("면",)},
    )

    contains_stmt = next(s for s in statements if s.name == "menu_ingredient:짜장면:면")
    assert "MERGE (ingredient:Ingredient {normalized_name: $ingredient_name})" in contains_stmt.cypher
    assert "MERGE (menu)-[c:CONTAINS]->(ingredient)" in contains_stmt.cypher
    assert "c.source" in contains_stmt.cypher
    assert contains_stmt.params == {
        "menu_name": "짜장면",
        "ingredient_name": "면",
        "ingredient_source": "CSV_FALLBACK",
        "source_url": "",
        "ingredient_confidence": 0.5,
        "fallback_used": True,
    }


def test_build_meal_restaurant_statements_skips_contains_for_unmapped_menu(tmp_path: Path):
    jsonl_file = tmp_path / "meal.jsonl"
    record = {
        "store": {
            "entity_id": "store-bibim",
            "name": "비빔밥집",
            "address_detail": "서울 종로구",
            "rating": 4.2,
            "canonical_url": "https://example.com/bibim",
        },
        "menus": [{"name": "비빔밥", "price": 9000}],
        "reviews": [],
    }
    jsonl_file.write_text(json.dumps(record, ensure_ascii=False) + "\n", encoding="utf-8")

    statements = build_meal_restaurant_statements(
        jsonl_file,
        menu_ingredient_map={"짜장면": ("면",)},
    )

    names = [s.name for s in statements]
    assert "restaurant_menu:https://example.com/bibim:비빔밥" in names
    assert not any("menu_ingredient" in name for name in names)


def test_build_meal_restaurant_statements_deduplicates_contains_across_restaurants(tmp_path: Path):
    jsonl_file = tmp_path / "meal.jsonl"
    records = [
        {
            "store": {"name": "중국집A", "address_detail": "서울", "rating": 4.0, "canonical_url": "https://example.com/a"},
            "menus": [{"name": "짜장면", "price": 8000}],
            "reviews": [],
        },
        {
            "store": {"name": "중국집B", "address_detail": "서울", "rating": 4.1, "canonical_url": "https://example.com/b"},
            "menus": [{"name": "짜장면", "price": 8500}],
            "reviews": [],
        },
    ]
    jsonl_file.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in records) + "\n",
        encoding="utf-8",
    )

    ingredient_map = {"짜장면": ("면",)}
    statements = build_meal_restaurant_statements(jsonl_file, menu_ingredient_map=ingredient_map)
    contains_statements = [s for s in statements if s.name == "menu_ingredient:짜장면:면"]
    assert len(contains_statements) == 2

    from kag_graph.hive_importer import _dedupe_by_name
    deduped = _dedupe_by_name(statements)
    deduped_contains = [s for s in deduped if s.name == "menu_ingredient:짜장면:면"]
    assert len(deduped_contains) == 1


def test_build_menu_ingredient_map_reads_csv_and_returns_tuples(tmp_path: Path):
    csv_file = tmp_path / "menu_ingredient.csv"
    csv_file.write_text(
        "menu_name,ingredient_name\n짜장면,면\n짬뽕,면\n된장찌개,된장\n초밥,오이\n",
        encoding="utf-8",
    )

    result = build_menu_ingredient_map(csv_file)

    assert result["짜장면"] == ("면",)
    assert result["짬뽕"] == ("면",)
    assert result["된장찌개"] == ("된장",)
    assert result["초밥"] == ("오이",)


def test_build_menu_ingredient_map_returns_empty_dict_when_file_missing(tmp_path: Path):
    result = build_menu_ingredient_map(tmp_path / "nonexistent.csv")

    assert result == {}


def test_load_graph_statements_runs_cypher_with_params(tmp_path: Path):
    driver = FakeDriver()
    news_file = tmp_path / "news.csv"
    _write_news_csv(news_file)
    statements = build_it_news_article_statements(news_file)

    loaded = load_graph_statements(driver, "neo4j", statements)

    assert loaded == ["news_article:geeknews_1"]
    assert driver.database == "neo4j"
    assert driver.session_obj.executed[0][1]["article_id"] == "geeknews_1"


def _write_news_csv(path: Path) -> None:
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=["title", "content", "thread", "article_url", "created_at", "author", "category_cd", "_page_service"],
        )
        writer.writeheader()
        writer.writerow(
            {
                "title": "Personal essay about development habits",
                "content": "No configured graph condition appears here.",
                "thread": "geeknews_1",
                "article_url": "https://example.com/a",
                "created_at": "2026-05-05 13:25:16",
                "author": "tester",
                "category_cd": "IC02",
                "_page_service": "geeknews",
            }
        )


def _write_address_code_csv(path: Path) -> None:
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=["cd", "name", "cd_info", "cd_upper"])
        writer.writeheader()
        writer.writerow(
            {
                "cd": "LA143",
                "name": "서울특별시 강남구",
                "cd_info": "주소",
                "cd_upper": "LA00",
            }
        )
        writer.writerow(
            {
                "cd": "SC01",
                "name": "한식",
                "cd_info": "shop",
                "cd_upper": "SC00",
            }
        )


class FakeSession:
    def __init__(self):
        self.executed = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def run(self, cypher: str, params: dict[str, object]):
        self.executed.append((cypher, params))


class FakeDriver:
    def __init__(self):
        self.session_obj = FakeSession()
        self.database = None

    def session(self, database: str):
        self.database = database
        return self.session_obj


def test_find_meal_recipe_success_files_matches_recipe_process_partition(tmp_path: Path):
    root = tmp_path / "meal"
    success_file = root / "process=recipe/category_cd=CA01/shop_cd=SC01/year=2026/month=05/day=12/status=success/recipe_collection_20260512_SC01_001_260512120000_att1.jsonl"
    success_file.parent.mkdir(parents=True)
    success_file.write_text("{}\n", encoding="utf-8")
    ignored = root / "process=cleaning/category_cd=CA01/shop_cd=SC01/year=2026/month=05/day=12/status=success/validation_normalization_20260512_SC01_001_260512120000_att1.jsonl"
    ignored.parent.mkdir(parents=True)
    ignored.write_text("{}\n", encoding="utf-8")

    files = find_meal_recipe_success_files(root)

    assert files == [success_file]


def test_build_recipe_ingredient_map_uses_first_recipe_ingredients_by_keyword(tmp_path: Path):
    recipe_file = tmp_path / "recipe_collection.jsonl"
    records = [
        {
            "recipe_search_keyword": "제육볶음",
            "recipe_url": "https://www.10000recipe.com/recipe/111",
            "ingredients": [{"ingredient_name": "돼지고기"}, {"ingredient_name": "고추장"}],
        },
        {
            "recipe_search_keyword": "제육볶음",
            "recipe_url": "https://www.10000recipe.com/recipe/222",
            "ingredients": [{"ingredient_name": "돼지고기"}, {"ingredient_name": "대파"}],
        },
        {
            "recipe_search_keyword": "된장찌개",
            "recipe_url": "https://www.10000recipe.com/recipe/333",
            "ingredients": [{"ingredient_name": "된장"}, {"ingredient_name": "두부"}],
        },
    ]
    recipe_file.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in records) + "\n",
        encoding="utf-8",
    )

    result = build_recipe_ingredient_map([recipe_file])

    assert {i["ingredient_name"] for i in result["제육볶음"]} == {"돼지고기", "고추장"}
    assert {i["ingredient_name"] for i in result["된장찌개"]} == {"된장", "두부"}
    # 첫 번째 레시피 URL이 돼지고기에 연결되어 있어야 함
    pork = next(i for i in result["제육볶음"] if i["ingredient_name"] == "돼지고기")
    assert pork["recipe_url"] == "https://www.10000recipe.com/recipe/111"


def test_build_meal_restaurant_statements_uses_recipe_ingredients_over_csv(tmp_path: Path):
    jsonl_file = tmp_path / "meal.jsonl"
    record = {
        "store": {
            "name": "제육집",
            "address_detail": "서울 강남구",
            "rating": 4.0,
            "canonical_url": "https://example.com/pork",
        },
        "menus": [
            {
                "name": "직화제육",
                "raw_menu_name": "직화제육",
                "normalized_name": "제육볶음",
                "canonical_name": "제육볶음",
                "recipe_search_keyword": "제육볶음",
                "menu_normalization_status": "NORMALIZED",
                "menu_confidence": 0.94,
                "normalization_method": "RULE_SIMILARITY",
                "price": 12000,
            }
        ],
        "reviews": [],
    }
    jsonl_file.write_text(json.dumps(record, ensure_ascii=False) + "\n", encoding="utf-8")

    recipe_map = {
        "제육볶음": [
            {"ingredient_name": "돼지고기", "recipe_url": "https://www.10000recipe.com/recipe/111"},
            {"ingredient_name": "고추장", "recipe_url": "https://www.10000recipe.com/recipe/111"},
        ]
    }
    csv_map = {"제육볶음": ("감자",)}  # CSV 폴백은 무시되어야 함

    statements = build_meal_restaurant_statements(
        jsonl_file,
        menu_ingredient_map=csv_map,
        recipe_ingredient_map=recipe_map,
    )

    names = [s.name for s in statements]
    assert "menu_ingredient:제육볶음:돼지고기" in names
    assert "menu_ingredient:제육볶음:고추장" in names
    assert "menu_ingredient:제육볶음:감자" not in names  # CSV 폴백 억제 확인

    pork_stmt = next(s for s in statements if s.name == "menu_ingredient:제육볶음:돼지고기")
    assert pork_stmt.params["ingredient_source"] == "RECIPE_10000"
    assert pork_stmt.params["ingredient_confidence"] == 0.9
    assert pork_stmt.params["fallback_used"] is False
    assert pork_stmt.params["source_url"] == "https://www.10000recipe.com/recipe/111"


def test_build_meal_restaurant_statements_falls_back_to_csv_when_no_recipe(tmp_path: Path):
    jsonl_file = tmp_path / "meal.jsonl"
    record = {
        "store": {
            "name": "짜장면집",
            "address_detail": "서울 강남구",
            "rating": 4.0,
            "canonical_url": "https://example.com/noodle",
        },
        "menus": [{"name": "짜장면", "price": 8000}],
        "reviews": [],
    }
    jsonl_file.write_text(json.dumps(record, ensure_ascii=False) + "\n", encoding="utf-8")

    statements = build_meal_restaurant_statements(
        jsonl_file,
        menu_ingredient_map={"짜장면": ("면",)},
        recipe_ingredient_map={},  # 레시피 데이터 없음
    )

    contains = next(s for s in statements if "menu_ingredient" in s.name)
    assert contains.params["ingredient_source"] == "CSV_FALLBACK"
    assert contains.params["ingredient_confidence"] == 0.5
    assert contains.params["fallback_used"] is True


def test_collect_current_hive_statements_reads_recipe_files_from_meal_root(tmp_path: Path):
    it_root = tmp_path / "it"
    meal_root = tmp_path / "meal"

    meal_file = meal_root / "process=cleaning/category_cd=CA01/shop_cd=SC01/year=2026/month=05/day=12/status=success/validation_normalization_20260512_SC01_001_260512120000_att1.jsonl"
    meal_file.parent.mkdir(parents=True)
    record = {
        "store": {
            "name": "제육집",
            "address_detail": "서울 강남구",
            "rating": 4.0,
            "canonical_url": "https://example.com/pork",
        },
        "menus": [
            {
                "name": "직화제육",
                "raw_menu_name": "직화제육",
                "normalized_name": "제육볶음",
                "recipe_search_keyword": "제육볶음",
                "menu_normalization_status": "NORMALIZED",
                "price": 12000,
            }
        ],
        "reviews": [],
    }
    meal_file.write_text(json.dumps(record, ensure_ascii=False) + "\n", encoding="utf-8")

    recipe_file = meal_root / "process=recipe/category_cd=CA01/shop_cd=SC01/year=2026/month=05/day=12/status=success/recipe_collection_20260512_SC01_001_260512120000_att1.jsonl"
    recipe_file.parent.mkdir(parents=True)
    recipe_record = {
        "recipe_search_keyword": "제육볶음",
        "recipe_url": "https://www.10000recipe.com/recipe/111",
        "ingredients": [{"ingredient_name": "돼지고기"}],
    }
    recipe_file.write_text(json.dumps(recipe_record, ensure_ascii=False) + "\n", encoding="utf-8")

    it_root.mkdir(parents=True)

    statements = collect_current_hive_statements(meal_root=meal_root, it_news_root=it_root)

    names = [s.name for s in statements]
    assert "menu_ingredient:제육볶음:돼지고기" in names
    contains = next(s for s in statements if s.name == "menu_ingredient:제육볶음:돼지고기")
    assert contains.params["ingredient_source"] == "RECIPE_10000"


def _write_meal_jsonl(
    path: Path,
    address_cd: str | None = None,
    canonical_url: str | None = SAMPLE_RESTAURANT_URL,
) -> None:
    record = {
        "store": {
            "entity_id": "LA143",
            "name": "동화고옥 선릉점",
            "address_detail": "서울 강남구",
            "rating": 4.8,
            "canonical_url": canonical_url,
        },
        "menus": [{"name": "불고기", "price": 39000}],
        "reviews": [{"keywords": ["조용한"]}],
    }
    if address_cd is not None:
        record["store"]["address_cd"] = address_cd
    path.write_text(json.dumps(record, ensure_ascii=False) + "\n", encoding="utf-8")
