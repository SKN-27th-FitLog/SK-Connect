import csv
import json
from dataclasses import dataclass
from pathlib import Path

from kag_graph.news_classifier import NewsClassifier, NewsClassificationResult, NewsConditionTerm


IT_NEWS_CLEANING_GLOB = "process=cleaning/category_cd=IC02/year=*/month=*/day=*/status=success/*.csv"
MEAL_LEGACY_CLEANSING_GLOB = (
    "crawling=cleansing/service=*/year=*/month=*/day=*/stage=validation_normalization/"
    "batch_id=*/status=success/*.jsonl"
)
MEAL_PROCESS_CLEANSING_GLOB = (
    "process=cleansing/category_cd=*/year=*/month=*/day=*/status=success/"
    "validation_normalization_*.jsonl"
)

NEWS_ARTICLE_CYPHER = """
MERGE (article:NewsArticle {article_id: $article_id})
SET article.title = $title,
    article.content = $content,
    article.summary = $summary,
    article.url = $url,
    article.source = $source,
    article.author = $author,
    article.category_cd = $category_cd,
    article.published_at = datetime($created_at),
    article.importance_score = $importance_score
"""

RESTAURANT_CYPHER = """
MERGE (restaurant:Restaurant {restaurant_id: $restaurant_id})
SET restaurant.name = $name,
    restaurant.address = $address,
    restaurant.url = $url,
    restaurant.rating = $rating,
    restaurant.is_active = true
"""

RESTAURANT_MENU_CYPHER = """
MATCH (restaurant:Restaurant {restaurant_id: $restaurant_id})
MERGE (menu:Menu {normalized_name: $menu_name})
SET menu.name = $menu_name,
    menu.price = $price,
    menu.menu_type = "dish"
MERGE (restaurant)-[:SELLS]->(menu)
"""

RESTAURANT_TAG_CYPHER = """
MATCH (restaurant:Restaurant {restaurant_id: $restaurant_id})
MERGE (tag:Tag {normalized_name: $tag_name})
SET tag.name = $tag_name,
    tag.tag_type = "review_keyword"
MERGE (restaurant)-[:HAS_TAG]->(tag)
"""

NEWS_TECHNOLOGY_CYPHER = """
MATCH (article:NewsArticle {article_id: $article_id})
MERGE (technology:Technology {normalized_name: $normalized_name})
SET technology.name = $name,
    technology.technology_type = $kind,
    technology.technology_id = $identifier
MERGE (article)-[:MENTIONS_TECH]->(technology)
"""

NEWS_COMPANY_CYPHER = """
MATCH (article:NewsArticle {article_id: $article_id})
MERGE (company:Company {normalized_name: $normalized_name})
SET company.name = $name,
    company.company_type = $kind,
    company.company_id = $identifier
MERGE (article)-[:MENTIONS_COMPANY]->(company)
"""

NEWS_EVENT_CYPHER = """
MATCH (article:NewsArticle {article_id: $article_id})
MERGE (event:Event {normalized_name: $normalized_name})
SET event.name = $name,
    event.event_type = $kind,
    event.event_id = $identifier
MERGE (article)-[:DESCRIBES_EVENT]->(event)
"""

NEWS_TOPIC_CYPHER = """
MATCH (article:NewsArticle {article_id: $article_id})
MERGE (topic:Topic {normalized_name: $normalized_name})
SET topic.name = $name,
    topic.topic_type = $kind,
    topic.topic_id = $identifier
MERGE (article)-[:MENTIONS]->(topic)
"""


@dataclass(frozen=True)
class GraphWriteStatement:
    name: str
    cypher: str
    params: dict[str, object]


def find_it_news_cleaning_success_files(root: Path) -> list[Path]:
    return _sorted_files(root, IT_NEWS_CLEANING_GLOB)


def find_meal_legacy_cleansing_success_files(root: Path) -> list[Path]:
    return _sorted_files(root, MEAL_LEGACY_CLEANSING_GLOB)


def find_meal_process_cleansing_success_files(root: Path) -> list[Path]:
    return _sorted_files(root, MEAL_PROCESS_CLEANSING_GLOB)


def build_it_news_article_statements(csv_file: Path) -> list[GraphWriteStatement]:
    statements: list[GraphWriteStatement] = []
    classifier = NewsClassifier()
    with csv_file.open("r", encoding="utf-8", newline="") as file:
        for row in csv.DictReader(file):
            article_id = _required_value(row, "thread")
            title = _required_value(row, "title")
            content = row.get("content", "")
            statements.append(
                GraphWriteStatement(
                    name=f"news_article:{article_id}",
                    cypher=NEWS_ARTICLE_CYPHER,
                    params={
                        "article_id": article_id,
                        "title": title,
                        "content": content,
                        "summary": _summary_from_content(content),
                        "url": row.get("article_url", ""),
                        "source": row.get("_page_service", ""),
                        "author": row.get("author", ""),
                        "category_cd": row.get("category_cd", ""),
                        "created_at": _created_at_for_neo4j(row.get("created_at", "")),
                        "importance_score": _importance_score(row),
                    },
                )
            )
            classification = classifier.classify(title=title, content=content)
            statements.extend(_build_news_condition_statements(article_id, classification))
    return statements


def build_meal_restaurant_statements(jsonl_file: Path) -> list[GraphWriteStatement]:
    statements: list[GraphWriteStatement] = []
    with jsonl_file.open("r", encoding="utf-8") as file:
        for line in file:
            if not line.strip():
                continue
            statements.extend(_build_meal_record_statements(json.loads(line)))
    return statements


def collect_legacy_once_statements(meal_root: Path, it_news_root: Path) -> list[GraphWriteStatement]:
    statements: list[GraphWriteStatement] = []
    for meal_file in find_meal_legacy_cleansing_success_files(meal_root):
        statements.extend(build_meal_restaurant_statements(meal_file))
    for news_file in find_it_news_cleaning_success_files(it_news_root):
        statements.extend(build_it_news_article_statements(news_file))
    return _dedupe_by_name(statements)


def collect_current_hive_statements(meal_root: Path, it_news_root: Path) -> list[GraphWriteStatement]:
    statements: list[GraphWriteStatement] = []
    for meal_file in find_meal_process_cleansing_success_files(meal_root):
        statements.extend(build_meal_restaurant_statements(meal_file))
    for news_file in find_it_news_cleaning_success_files(it_news_root):
        statements.extend(build_it_news_article_statements(news_file))
    return _dedupe_by_name(statements)


def load_graph_statements(driver, database: str, statements: list[GraphWriteStatement]) -> list[str]:
    loaded: list[str] = []
    with driver.session(database=database) as session:
        for statement in statements:
            session.run(statement.cypher, statement.params)
            loaded.append(statement.name)
    return loaded


def _sorted_files(root: Path, pattern: str) -> list[Path]:
    if not root.exists():
        return []
    return sorted(path for path in root.glob(pattern) if path.is_file())


def _dedupe_by_name(statements: list[GraphWriteStatement]) -> list[GraphWriteStatement]:
    deduped: list[GraphWriteStatement] = []
    seen: set[str] = set()
    for statement in statements:
        if statement.name in seen:
            continue
        seen.add(statement.name)
        deduped.append(statement)
    return deduped


def _build_meal_record_statements(record: dict[str, object]) -> list[GraphWriteStatement]:
    store = record.get("store")
    if not isinstance(store, dict):
        raise ValueError("meal record requires store object")

    restaurant_id = _required_value(store, "entity_id")
    statements = [
        GraphWriteStatement(
            name=f"restaurant:{restaurant_id}",
            cypher=RESTAURANT_CYPHER,
            params={
                "restaurant_id": restaurant_id,
                "name": _required_value(store, "name"),
                "address": store.get("address_detail", ""),
                "url": store.get("canonical_url", ""),
                "rating": _float_or_none(store.get("rating")),
            },
        )
    ]

    statements.extend(_build_menu_statements(restaurant_id, record.get("menus", [])))
    statements.extend(_build_tag_statements(restaurant_id, record.get("reviews", [])))
    return statements


def _build_news_condition_statements(
    article_id: str,
    classification: NewsClassificationResult,
) -> list[GraphWriteStatement]:
    statements: list[GraphWriteStatement] = []
    statements.extend(_build_news_term_statements(article_id, "news_technology", NEWS_TECHNOLOGY_CYPHER, classification.technologies))
    statements.extend(_build_news_term_statements(article_id, "news_company", NEWS_COMPANY_CYPHER, classification.companies))
    statements.extend(_build_news_term_statements(article_id, "news_event", NEWS_EVENT_CYPHER, classification.events))
    statements.extend(_build_news_term_statements(article_id, "news_topic", NEWS_TOPIC_CYPHER, classification.topics))
    return statements


def _build_news_term_statements(
    article_id: str,
    name_prefix: str,
    cypher: str,
    terms: list[NewsConditionTerm],
) -> list[GraphWriteStatement]:
    return [
        GraphWriteStatement(
            name=f"{name_prefix}:{article_id}:{term.normalized_name}",
            cypher=cypher,
            params={
                "article_id": article_id,
                "normalized_name": term.normalized_name,
                "name": term.name,
                "kind": term.kind,
                "identifier": term.identifier,
            },
        )
        for term in terms
    ]


def _build_menu_statements(restaurant_id: str, menus: object) -> list[GraphWriteStatement]:
    if not isinstance(menus, list):
        return []

    statements: list[GraphWriteStatement] = []
    seen: set[str] = set()
    for menu in menus:
        if not isinstance(menu, dict):
            continue
        menu_name = str(menu.get("name", "")).strip()
        if not menu_name or menu_name in seen:
            continue
        seen.add(menu_name)
        statements.append(
            GraphWriteStatement(
                name=f"restaurant_menu:{restaurant_id}:{menu_name}",
                cypher=RESTAURANT_MENU_CYPHER,
                params={
                    "restaurant_id": restaurant_id,
                    "menu_name": menu_name,
                    "price": _int_or_zero(menu.get("price")),
                },
            )
        )
    return statements


def _build_tag_statements(restaurant_id: str, reviews: object) -> list[GraphWriteStatement]:
    if not isinstance(reviews, list):
        return []

    statements: list[GraphWriteStatement] = []
    seen: set[str] = set()
    for review in reviews:
        if not isinstance(review, dict):
            continue
        keywords = review.get("keywords", [])
        if not isinstance(keywords, list):
            continue
        for keyword in keywords:
            tag_name = str(keyword).strip()
            if not tag_name or tag_name in seen:
                continue
            seen.add(tag_name)
            statements.append(
                GraphWriteStatement(
                    name=f"restaurant_tag:{restaurant_id}:{tag_name}",
                    cypher=RESTAURANT_TAG_CYPHER,
                    params={"restaurant_id": restaurant_id, "tag_name": tag_name},
                )
            )
    return statements


def _required_value(row: dict[str, object], key: str) -> str:
    value = str(row.get(key, "")).strip()
    if not value:
        raise ValueError(f"{key} is required")
    return value


def _summary_from_content(content: str) -> str:
    text = " ".join(content.split())
    return text[:300]


def _created_at_for_neo4j(value: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        return "1970-01-01T00:00:00"
    return cleaned.replace(" ", "T", 1)


def _importance_score(row: dict[str, object]) -> float:
    point = _float_or_none(row.get("point"))
    if point is None:
        return 0.0
    return point


def _float_or_none(value: object) -> float | None:
    if value in (None, ""):
        return None
    return float(value)


def _int_or_zero(value: object) -> int:
    if value in (None, ""):
        return 0
    return int(float(value))
