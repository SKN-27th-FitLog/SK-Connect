from src.collectors.base_collector import BaseCollector
from src.core.policy.exceptions import NetworkException
from src.core.policy.reason_code import ReasonCode
from playwright.async_api import async_playwright, Page
import logging
import asyncio
import urllib.parse
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

async def apply_manual_stealth(page: Page):
    """브라우저 자동화 탐지를 피하기 위한 수동 스텔스 스크립트 주입."""
    await page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    await page.add_init_script("window.chrome = { runtime: {} };")
    await page.add_init_script("Object.defineProperty(navigator, 'languages', {get: () => ['ko-KR', 'ko', 'en-US', 'en']})")

class DiningCodeCollector(BaseCollector):
    def get_platform_name(self) -> str:
        return "DiningCode"

    async def _get_page(self, playwright, headless: bool = True) -> Any:
        browser = await playwright.chromium.launch(headless=headless)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        await apply_manual_stealth(page)
        return browser, page

    async def discover_stores(self, query: str, limit: int = 10) -> List[str]:
        """검색 쿼리를 바탕으로 매장 프로필 URL 목록 추출"""
        encoded_query = urllib.parse.quote(query)
        search_url = f"https://www.diningcode.com/list.php?query={encoded_query}"
        
        async with async_playwright() as p:
            browser, page = await self._get_page(p)
            try:
                logger.info(f"Discovering stores for query: {query}")
                await page.goto(search_url, wait_until="domcontentloaded", timeout=40000)
                
                # 리스트 아이템이 나타날 때까지 대기
                await page.wait_for_selector('a.PoiBlock', timeout=15000)
                
                # 프로필 링크 추출 (PoiBlock 클래스 사용)
                links = await page.eval_on_selector_all(
                    'a.PoiBlock', 
                    "elements => elements.map(el => el.href)"
                )
                
                # 중복 제거 및 리미트 적용 (profile.php 포함된 링크만)
                profile_links = [l for l in links if "profile.php" in l]
                unique_links = list(dict.fromkeys(profile_links))[:limit]
                
                logger.info(f"Found {len(unique_links)} profile links for query: {query}")
                return unique_links
            except Exception as e:
                logger.error(f"Discovery failed for {query}: {str(e)}")
                return []
            finally:
                await browser.close()

    async def collect(self, target_url: str, **kwargs) -> Dict[str, Any]:
        """개별 매장 프로필 페이지 수집"""
        async with async_playwright() as p:
            browser, page = await self._get_page(p)
            try:
                await page.goto(target_url, wait_until="domcontentloaded", timeout=40000)
                
                # 데이터 렌더링 대기
                try:
                    await page.wait_for_selector('div.tit', timeout=15000)
                except:
                    logger.warning("Timeout waiting for 'div.tit'")

                # 지연 로딩 강제 활성화를 위한 스크롤
                for _ in range(2):
                    await page.evaluate("window.scrollBy(0, 1000)")
                    await asyncio.sleep(1)
                
                content = await page.content()
                return {
                    "raw_content": content,
                    "platform": self.get_platform_name(),
                    "url": target_url
                }
            except Exception as e:
                raise NetworkException(ReasonCode.TIMEOUT, "raw_collection", "html", str(e))
            finally:
                await browser.close()
