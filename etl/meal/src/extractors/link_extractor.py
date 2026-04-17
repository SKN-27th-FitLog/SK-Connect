import re
from typing import List, Dict, Set, Final, Optional
from urllib.parse import urljoin
from playwright.sync_api import Page, Locator, TimeoutError as PlaywrightTimeoutError
import pandas as pd
from ..core.base_crawler import BaseCrawler
from ..core.file_manager import logger

class LinkExtractor(BaseCrawler):
    """
    다이닝코드 목록 페이지에서 식당 상세 페이지 URL을 수집합니다.
    """
    
    BASE_URL: Final[str] = "https://www.diningcode.com"
    LISTING_URL_TEMPLATE: Final[str] = "https://www.diningcode.com/list.dc?query={region}%20{category}"
    RANK_PREFIX_PATTERN: Final[re.Pattern] = re.compile(r"^\d+\.\s*")

    def __init__(self, headless: bool = True):
        super().__init__(headless=headless)

    def _scroll_listing_page(self, page: Page, rounds: int = 5):
        """목록 페이지를 아래로 스크롤하여 동적 로딩된 카드를 노출시킵니다."""
        for _ in range(rounds):
            try:
                page.mouse.wheel(0, 2200)
                page.wait_for_timeout(700)
            except Exception:
                break

    def _collect_cards_on_page(self, page: Page) -> List[Dict[str, str]]:
        """현재 페이지에서 맛집 카드 정보를 추출합니다."""
        candidates: List[Dict[str, str]] = []
        seen: Set[str] = set()

        # 식당 링크가 포함된 anchor 셀렉터
        selectors = ["a[href*='profile.php?rid=']", "a[href*='/profile.php?rid=']"]

        for selector in selectors:
            anchors = page.locator(selector)
            try:
                count = min(anchors.count(), 100)
            except Exception:
                count = 0

            for idx in range(count):
                anchor = anchors.nth(idx)
                href = anchor.get_attribute("href")
                text = self.safe_text(anchor)
                
                if not href:
                    continue
                
                full_url = urljoin(self.BASE_URL, href)
                if full_url in seen:
                    continue
                
                lines = [line.strip() for line in text.splitlines() if line.strip()]
                if not lines:
                    continue
                
                # 이름 및 요약 추출 로직 (기존 정규식/순위 제거 반영)
                first_line = lines[0]
                if re.match(r"^\d+\.$", first_line) and len(lines) > 1:
                    raw_name = lines[1]
                    store_summary = " | ".join(lines[2:5])
                else:
                    raw_name = first_line
                    store_summary = " | ".join(lines[1:4])

                clean_name = self.RANK_PREFIX_PATTERN.sub("", raw_name).strip()
                
                candidates.append({
                    "store_name": clean_name,
                    "store_url": full_url,
                    "store_summary": store_summary,
                })
                seen.add(full_url)
        return candidates

    def extract_links(self, region: str, category: str, max_pages: int = 3) -> List[Dict[str, str]]:
        """특정 지역 및 카테고리에 대해 여러 페이지를 탐합합니다."""
        rows: List[Dict[str, str]] = []

        def run_task(page: Page):
            for page_no in range(1, max_pages + 1):
                listing_url = self.LISTING_URL_TEMPLATE.format(region=region, category=category)
                if page_no > 1:
                    listing_url = f"{listing_url}&page={page_no}"

                logger.info(f"  -> [{region} {category}] {page_no}페이지 탐색 중...")
                try:
                    page.goto(listing_url, wait_until="domcontentloaded", timeout=60000)
                    page.wait_for_timeout(1500)
                    self._scroll_listing_page(page, rounds=4)
                    
                    cards = self._collect_cards_on_page(page)
                    if not cards:
                        break

                    for card in cards:
                        rows.append({
                            "source_region": region,
                            "source_category": category,
                            "page_no": str(page_no),
                            "store_name": card["store_name"],
                            "store_url": card["store_url"],
                            "store_summary": card["store_summary"],
                            "collected_at": pd.Timestamp.now().isoformat(),
                            "status": "ok",
                        })
                except Exception as e:
                    logger.error(f"!!! [{region} {category}] 수집 중 오류: {str(e)}")
                    break
            return rows

        return self.run(run_task)
