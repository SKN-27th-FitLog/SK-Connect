import csv
import json
from pathlib import Path

from kag_graph.hive_importer import (
    build_it_news_article_statements,
    build_meal_restaurant_statements,
    collect_current_hive_statements,
    collect_legacy_once_statements,
    find_it_news_cleaning_success_files,
    find_meal_legacy_cleansing_success_files,
    find_meal_process_cleansing_success_files,
    load_graph_statements,
)


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
    ignored = root / "process=cleansing/category_cd=SC01/year=2026/month=05/day=05/status=success/validation_normalization_20260505_SC01_001_260505083633_att1.jsonl"
    ignored.parent.mkdir(parents=True)
    ignored.write_text("{}\n", encoding="utf-8")

    files = find_meal_legacy_cleansing_success_files(root)

    assert files == [success_file]


def test_find_meal_process_cleansing_success_files_uses_current_hive_partition(tmp_path: Path):
    root = tmp_path / "meal"
    success_file = root / "process=cleansing/category_cd=SC01/year=2026/month=05/day=05/status=success/validation_normalization_20260505_SC01_001_260505083633_att1.jsonl"
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
        "restaurant:LA143",
        "restaurant_menu:LA143:불고기",
        "restaurant_tag:LA143:조용한",
        "restaurant_tag:LA143:깔끔한",
    ]
    assert statements[0].params["restaurant_id"] == "LA143"
    assert statements[1].params["menu_name"] == "불고기"
    assert statements[2].params["tag_name"] == "조용한"


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
        "restaurant:LA143",
        "restaurant_menu:LA143:불고기",
        "restaurant_tag:LA143:조용한",
        "news_article:geeknews_1",
    ]


def test_collect_current_hive_statements_reads_it_news_cleaning_and_meal_process(tmp_path: Path):
    it_root = tmp_path / "it"
    meal_root = tmp_path / "meal"
    news_file = it_root / "process=cleaning/category_cd=IC02/year=2026/month=05/day=05/status=success/it_news.csv"
    news_file.parent.mkdir(parents=True)
    _write_news_csv(news_file)
    meal_file = meal_root / "process=cleansing/category_cd=SC01/year=2026/month=05/day=05/status=success/validation_normalization_20260505_SC01_001_260505083633_att1.jsonl"
    meal_file.parent.mkdir(parents=True)
    _write_meal_jsonl(meal_file)

    statements = collect_current_hive_statements(meal_root=meal_root, it_news_root=it_root)

    assert [statement.name for statement in statements] == [
        "restaurant:LA143",
        "restaurant_menu:LA143:불고기",
        "restaurant_tag:LA143:조용한",
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
        "restaurant:LA143",
        "restaurant_menu:LA143:불고기",
        "restaurant_tag:LA143:조용한",
        "news_article:geeknews_1",
    ]


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


def _write_meal_jsonl(path: Path) -> None:
    record = {
        "store": {
            "entity_id": "LA143",
            "name": "동화고옥 선릉점",
            "address_detail": "서울 강남구",
            "rating": 4.8,
            "canonical_url": "https://example.com/store",
        },
        "menus": [{"name": "불고기", "price": 39000}],
        "reviews": [{"keywords": ["조용한"]}],
    }
    path.write_text(json.dumps(record, ensure_ascii=False) + "\n", encoding="utf-8")
