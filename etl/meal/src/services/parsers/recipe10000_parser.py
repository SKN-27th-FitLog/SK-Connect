import re
from typing import Any, Dict, List

from bs4 import BeautifulSoup

from src.services.parsers.base_parser import BaseParser


QUANTITY_SUFFIX_PATTERN = re.compile(
    r"\s+(?:약간|적당량|조금|취향껏|[0-9]+(?:/[0-9]+)?(?:\.[0-9]+)?\s*"
    r"(?:g|kg|ml|l|개|대|쪽|알|큰술|작은술|스푼|컵|줌|장|봉|팩|캔|꼬집|T|t))$",
    re.IGNORECASE,
)


class Recipe10000Parser(BaseParser):
    """만개의레시피 recipe detail HTML parser."""

    def parse_shop(self, html: str) -> Dict[str, Any]:
        return {}

    def parse_menus(self, html: str) -> List[Dict[str, Any]]:
        return []

    def parse_reviews(self, html: str) -> List[Dict[str, Any]]:
        return []

    def parse_images(self, html: str) -> List[str]:
        return []

    def parse_recipe_metadata(self, html: str) -> Dict[str, Any]:
        soup = BeautifulSoup(html, "html.parser")
        title_tag = soup.select_one(".view2_summary h3, .view2_summary.st3 h3, h3")
        title = title_tag.get_text(strip=True) if title_tag else ""
        canonical_url_tag = soup.find("link", rel="canonical")
        recipe_url = canonical_url_tag.get("href", "") if canonical_url_tag else ""
        return {
            "recipe_title": title,
            "recipe_url": recipe_url,
        }

    def parse_ingredients(self, html: str) -> List[Dict[str, str]]:
        soup = BeautifulSoup(html, "html.parser")
        ingredient_tags = soup.select("#divConfirmedMaterialArea li .ingre_list_name")

        ingredients: list[dict[str, str]] = []
        seen: set[str] = set()
        for tag in ingredient_tags:
            ingredient_name = normalize_ingredient_name(tag.get_text(" ", strip=True))
            if not ingredient_name or ingredient_name in seen:
                continue
            seen.add(ingredient_name)
            ingredients.append({"ingredient_name": ingredient_name})
        return ingredients


def normalize_ingredient_name(raw_text: str) -> str:
    name = re.sub(r"\s+", " ", raw_text).strip()
    previous = None
    while previous != name:
        previous = name
        name = QUANTITY_SUFFIX_PATTERN.sub("", name).strip()
    return name
