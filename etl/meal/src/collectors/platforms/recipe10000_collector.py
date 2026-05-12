import logging
import re
import urllib.parse
from typing import Any, Dict, List

from playwright.async_api import async_playwright

from src.collectors.base_collector import BaseCollector
from src.core.policy.exceptions import NetworkException
from src.core.policy.reason_code import ReasonCode


logger = logging.getLogger(__name__)


class Recipe10000Collector(BaseCollector):
    """만개의레시피 검색/상세 HTML 수집기."""

    BASE_URL = "https://www.10000recipe.com"
    SEARCH_PATH = "/recipe/list.html"

    def get_platform_name(self) -> str:
        return "Recipe10000"

    def build_search_url(self, recipe_search_keyword: str) -> str:
        encoded_keyword = urllib.parse.quote(recipe_search_keyword)
        return f"{self.BASE_URL}{self.SEARCH_PATH}?q={encoded_keyword}"

    async def discover_recipes(self, recipe_search_keyword: str, limit: int = 3) -> List[str]:
        """검색 키워드로 레시피 상세 페이지 URL 목록 추출."""
        search_url = self.build_search_url(recipe_search_keyword)
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=True)
            page = await browser.new_page()
            try:
                await page.goto(search_url, wait_until="domcontentloaded", timeout=40000)
                await page.wait_for_load_state("networkidle", timeout=10000)
                all_hrefs = await page.eval_on_selector_all(
                    "a", "elements => elements.map(el => el.href)"
                )
                recipe_links = list(dict.fromkeys(
                    href for href in all_hrefs
                    if re.search(r"/recipe/\d+$", href)
                ))[:limit]
                logger.info(f"Found {len(recipe_links)} recipe links for keyword: {recipe_search_keyword}")
                return recipe_links
            except Exception as exc:
                logger.warning(f"Recipe discovery failed for '{recipe_search_keyword}': {exc}")
                return []
            finally:
                await browser.close()

    async def collect(self, target_url: str, **kwargs) -> Dict[str, Any]:
        recipe_search_keyword = str(kwargs.get("recipe_search_keyword", "")).strip()
        url = target_url.strip() if target_url else self.build_search_url(recipe_search_keyword)

        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=True)
            page = await browser.new_page()
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=40000)
                await page.wait_for_load_state("networkidle", timeout=10000)
                content = await page.content()
                return {
                    "raw_content": content,
                    "platform": self.get_platform_name(),
                    "url": url,
                    "recipe_search_keyword": recipe_search_keyword,
                }
            except Exception as exc:
                raise NetworkException(
                    reason_code=ReasonCode.RECIPE_SEARCH_EMPTY,
                    stage="raw_collection",
                    entity_type="recipe",
                    detail=str(exc),
                ) from exc
            finally:
                await browser.close()
