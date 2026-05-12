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
MEAL_RECIPE_GLOB = (
    "process=recipe/category_cd=*/year=*/month=*/day=*/status=success/"
    "recipe_collection_*.jsonl"
)
ADDRESS_CODE_UPPER = "LA00"
PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_ADDRESS_CODE_TABLE = PROJECT_ROOT / "database/data/codeT.csv"
DEFAULT_MENU_INGREDIENT_TABLE = PROJECT_ROOT / "database/data/menu_ingredient.csv"

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
MERGE (menu:Menu {normalized_name: $normalized_name})
SET menu.name = $canonical_name,
    menu.canonical_name = $canonical_name,
    menu.menu_type = "dish"
MERGE (restaurant)-[s:SELLS]->(menu)
SET s.raw_menu_name = $raw_menu_name,
    s.display_menu_name = $display_menu_name,
    s.price = $price,
    s.recipe_search_keyword = $recipe_search_keyword,
    s.menu_confidence = $menu_confidence,
    s.menu_normalization_status = $menu_normalization_status,
    s.normalization_method = $normalization_method
"""

MENU_CONTAINS_INGREDIENT_CYPHER = """
MATCH (menu:Menu {normalized_name: $menu_name})
MERGE (ingredient:Ingredient {normalized_name: $ingredient_name})
SET ingredient.name = $ingredient_name
MERGE (menu)-[c:CONTAINS]->(ingredient)
SET c.source = $ingredient_source,
    c.source_url = $source_url,
    c.confidence = $ingredient_confidence,
    c.fallback_used = $fallback_used
"""

RESTAURANT_TAG_CYPHER = """
MATCH (restaurant:Restaurant {restaurant_id: $restaurant_id})
MERGE (tag:Tag {normalized_name: $tag_name})
SET tag.name = $tag_name,
    tag.tag_type = "review_keyword"
MERGE (restaurant)-[:HAS_TAG]->(tag)
"""

RESTAURANT_AREA_CYPHER = """
MATCH (restaurant:Restaurant {restaurant_id: $restaurant_id})
MERGE (area:Area {normalized_name: $address_name})
SET area.area_id = $address_cd,
    area.name = $address_name
MERGE (restaurant)-[:LOCATED_IN]->(area)
WITH restaurant, area
OPTIONAL MATCH (concept:Concept {normalized_name: area.normalized_name})
FOREACH (c IN CASE WHEN concept IS NOT NULL THEN [concept] ELSE [] END |
  MERGE (restaurant)-[:RELATED_TO]->(c)
)
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
WITH article, topic
OPTIONAL MATCH (concept:Concept {normalized_name: topic.normalized_name})
FOREACH (c IN CASE WHEN concept IS NOT NULL THEN [concept] ELSE [] END |
  MERGE (article)-[:RELATED_TO]->(c)
)
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


def find_meal_recipe_success_files(root: Path) -> list[Path]:
    return _sorted_files(root, MEAL_RECIPE_GLOB)


def build_address_name_map(code_table_file: Path) -> dict[str, str]:
    if not code_table_file.exists():
        return {}

    with code_table_file.open("r", encoding="utf-8-sig", newline="") as file:
        return {
            row["cd"].strip(): row["name"].strip()
            for row in csv.DictReader(file)
            if row.get("cd_upper", "").strip() == ADDRESS_CODE_UPPER
            and row.get("cd", "").strip()
            and row.get("name", "").strip()
        }


def build_recipe_ingredient_map(recipe_files: list[Path]) -> dict[str, list[dict]]:
    """recipe_collection JSONL에서 키워드별 재료 목록을 반환.

    반환 형식: {recipe_search_keyword: [{"ingredient_name": str, "recipe_url": str}]}
    동일 키워드에서 여러 레시피가 있으면 재료명 기준으로 중복 제거(첫 번째 URL 유지).
    """
    keyword_map: dict[str, dict[str, str]] = {}  # keyword → {ingredient_name: recipe_url}
    for file in recipe_files:
        with file.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                record = json.loads(line)
                keyword = record.get("recipe_search_keyword", "").strip()
                recipe_url = record.get("recipe_url", "")
                if not keyword:
                    continue
                seen = keyword_map.setdefault(keyword, {})
                for ing in record.get("ingredients", []):
                    name = ing.get("ingredient_name", "").strip()
                    if name and name not in seen:
                        seen[name] = recipe_url
    return {
        keyword: [{"ingredient_name": name, "recipe_url": url} for name, url in ings.items()]
        for keyword, ings in keyword_map.items()
    }


def build_menu_ingredient_map(table_file: Path) -> dict[str, tuple[str, ...]]:
    if not table_file.exists():
        return {}

    result: dict[str, list[str]] = {}
    with table_file.open("r", encoding="utf-8-sig", newline="") as file:
        for row in csv.DictReader(file):
            menu = row.get("menu_name", "").strip()
            ingredient = row.get("ingredient_name", "").strip()
            if menu and ingredient:
                result.setdefault(menu, []).append(ingredient)
    return {menu: tuple(ingredients) for menu, ingredients in result.items()}


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


def build_meal_restaurant_statements(
    jsonl_file: Path,
    address_name_map: dict[str, str] | None = None,
    menu_ingredient_map: dict[str, tuple[str, ...]] | None = None,
    recipe_ingredient_map: dict[str, list[dict]] | None = None,
) -> list[GraphWriteStatement]:
    statements: list[GraphWriteStatement] = []
    area_name_map = address_name_map or {}
    ingredient_map = menu_ingredient_map or {}
    recipe_map = recipe_ingredient_map or {}
    with jsonl_file.open("r", encoding="utf-8") as file:
        for line in file:
            if not line.strip():
                continue
            statements.extend(_build_meal_record_statements(json.loads(line), area_name_map, ingredient_map, recipe_map))
    return statements


def collect_legacy_once_statements(meal_root: Path, it_news_root: Path) -> list[GraphWriteStatement]:
    statements: list[GraphWriteStatement] = []
    address_name_map = build_address_name_map(DEFAULT_ADDRESS_CODE_TABLE)
    menu_ingredient_map = build_menu_ingredient_map(DEFAULT_MENU_INGREDIENT_TABLE)
    for meal_file in find_meal_legacy_cleansing_success_files(meal_root):
        statements.extend(build_meal_restaurant_statements(meal_file, address_name_map, menu_ingredient_map))
    for news_file in find_it_news_cleaning_success_files(it_news_root):
        statements.extend(build_it_news_article_statements(news_file))
    return _dedupe_by_name(statements)


def collect_current_hive_statements(meal_root: Path, it_news_root: Path) -> list[GraphWriteStatement]:
    statements: list[GraphWriteStatement] = []
    address_name_map = build_address_name_map(DEFAULT_ADDRESS_CODE_TABLE)
    menu_ingredient_map = build_menu_ingredient_map(DEFAULT_MENU_INGREDIENT_TABLE)
    recipe_ingredient_map = build_recipe_ingredient_map(find_meal_recipe_success_files(meal_root))
    for meal_file in find_meal_process_cleansing_success_files(meal_root):
        statements.extend(build_meal_restaurant_statements(meal_file, address_name_map, menu_ingredient_map, recipe_ingredient_map))
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


def _build_meal_record_statements(
    record: dict[str, object],
    address_name_map: dict[str, str],
    menu_ingredient_map: dict[str, tuple[str, ...]],
    recipe_ingredient_map: dict[str, list[dict]] | None = None,
) -> list[GraphWriteStatement]:
    store = record.get("store")
    if not isinstance(store, dict):
        raise ValueError("meal record requires store object")

    restaurant_id = _restaurant_id_from_store(store)
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

    area_statement = _build_area_statement(restaurant_id, store, address_name_map)
    if area_statement is not None:
        statements.append(area_statement)

    statements.extend(_build_menu_statements(restaurant_id, record.get("menus", []), menu_ingredient_map, recipe_ingredient_map))
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


def _build_area_statement(
    restaurant_id: str,
    store: dict[str, object],
    address_name_map: dict[str, str],
) -> GraphWriteStatement | None:
    address_cd = str(store.get("address_cd", "")).strip()
    if not address_cd or address_cd == "UNKNOWN":
        return None

    address_name = address_name_map.get(address_cd, address_cd)
    return GraphWriteStatement(
        name=f"restaurant_area:{restaurant_id}:{address_cd}",
        cypher=RESTAURANT_AREA_CYPHER,
        params={
            "restaurant_id": restaurant_id,
            "address_cd": address_cd,
            "address_name": address_name,
        },
    )


def _restaurant_id_from_store(store: dict[str, object]) -> str:
    canonical_url = str(store.get("canonical_url", "")).strip()
    if canonical_url:
        return canonical_url

    name = str(store.get("name", "")).strip()
    address = str(store.get("address_detail", "")).strip()
    if name and address:
        return f"{name}|{address}"

    return _required_value(store, "entity_id")


def _build_menu_statements(
    restaurant_id: str,
    menus: object,
    menu_ingredient_map: dict[str, tuple[str, ...]],
    recipe_ingredient_map: dict[str, list[dict]] | None = None,
) -> list[GraphWriteStatement]:
    if not isinstance(menus, list):
        return []

    statements: list[GraphWriteStatement] = []
    seen: set[str] = set()
    for menu in menus:
        if not isinstance(menu, dict):
            continue
        raw_menu_name = _menu_text(menu, "raw_menu_name", "name")
        if not raw_menu_name or raw_menu_name in seen:
            continue
        seen.add(raw_menu_name)
        normalized_name = _menu_text(menu, "normalized_name", "canonical_name", "name")
        canonical_name = _menu_text(menu, "canonical_name", "normalized_name", "name")
        display_menu_name = _menu_text(menu, "display_menu_name", "name")
        recipe_search_keyword = _nullable_menu_text(menu, "recipe_search_keyword")
        statements.append(
            GraphWriteStatement(
                name=f"restaurant_menu:{restaurant_id}:{raw_menu_name}",
                cypher=RESTAURANT_MENU_CYPHER,
                params={
                    "restaurant_id": restaurant_id,
                    "raw_menu_name": raw_menu_name,
                    "display_menu_name": display_menu_name,
                    "normalized_name": normalized_name,
                    "canonical_name": canonical_name,
                    "recipe_search_keyword": recipe_search_keyword,
                    "menu_confidence": _float_or_none(menu.get("menu_confidence")),
                    "menu_normalization_status": _menu_text(menu, "menu_normalization_status", default="UNSPECIFIED"),
                    "normalization_method": _menu_text(menu, "normalization_method", default="UNSPECIFIED"),
                    "price": _int_or_zero(menu.get("price")),
                },
            )
        )

        # 재료 연결: 레시피 데이터 우선, 없으면 CSV 폴백
        recipe_ingredients = (
            (recipe_ingredient_map or {}).get(recipe_search_keyword or "", [])
        )
        if recipe_ingredients:
            for ing in recipe_ingredients:
                ingredient_name = ing["ingredient_name"]
                statements.append(
                    GraphWriteStatement(
                        name=f"menu_ingredient:{normalized_name}:{ingredient_name}",
                        cypher=MENU_CONTAINS_INGREDIENT_CYPHER,
                        params={
                            "menu_name": normalized_name,
                            "ingredient_name": ingredient_name,
                            "ingredient_source": "RECIPE_10000",
                            "source_url": ing.get("recipe_url", ""),
                            "ingredient_confidence": 0.9,
                            "fallback_used": False,
                        },
                    )
                )
        else:
            for ingredient_name in menu_ingredient_map.get(normalized_name, menu_ingredient_map.get(raw_menu_name, ())):
                statements.append(
                    GraphWriteStatement(
                        name=f"menu_ingredient:{normalized_name}:{ingredient_name}",
                        cypher=MENU_CONTAINS_INGREDIENT_CYPHER,
                        params={
                            "menu_name": normalized_name,
                            "ingredient_name": ingredient_name,
                            "ingredient_source": "CSV_FALLBACK",
                            "source_url": "",
                            "ingredient_confidence": 0.5,
                            "fallback_used": True,
                        },
                    )
                )
    return statements


def _menu_text(menu: dict[str, object], *keys: str, default: str = "") -> str:
    for key in keys:
        value = str(menu.get(key, "")).strip()
        if value:
            return value
    return default


def _nullable_menu_text(menu: dict[str, object], key: str) -> str | None:
    value = str(menu.get(key, "")).strip()
    if not value:
        return None
    return value


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
