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

    async def _click_menu_more(self, page: Page):
        """'메뉴 더보기' 버튼 클릭하여 전체 메뉴 노출"""
        try:
            menu_more_btn = page.locator('span.more-btn')
            if await menu_more_btn.count() > 0 and await menu_more_btn.first.is_visible():
                await menu_more_btn.first.click()
                await asyncio.sleep(0.5)
                logger.debug("Clicked '메뉴 더보기' button")
        except Exception as e:
            logger.debug(f"Menu more button not found or not clickable: {e}")

    async def _click_review_more(self, page: Page, max_clicks: int = 20):
        """'평가 더보기' 버튼을 반복 클릭하여 전체 리뷰 로딩"""
        for i in range(max_clicks):
            try:
                review_btn = page.locator('button.More__Review__Button')
                if await review_btn.count() > 0 and await review_btn.first.is_visible():
                    await review_btn.first.click()
                    await asyncio.sleep(1.0)
                    logger.debug(f"Clicked '평가 더보기' button ({i + 1})")
                else:
                    break
            except Exception:
                break
        logger.debug(f"Review loading complete after {i + 1} attempts")

    async def _expand_review_contents(self, page: Page):
        """접힌 리뷰 '...더보기' 링크 클릭하여 전체 리뷰 본문 펼치기"""
        try:
            more_links = page.locator('a.more-btn')
            count = await more_links.count()
            for i in range(count):
                link = more_links.nth(i)
                if await link.is_visible():
                    await link.click()
                    await asyncio.sleep(0.3)
            if count > 0:
                logger.debug(f"Expanded {count} review contents")
        except Exception as e:
            logger.debug(f"Review content expansion failed: {e}")

    async def _collect_photo_tabs(self, page: Page):
        """사진 탭 (음식/실내/실외/메뉴·정보) 각각 클릭하여 이미지 data-origin 수집"""
        all_photos = {}
        tab_types = ['food', 'interior', 'exterior', 'menu_info']

        for tab_type in tab_types:
            try:
                tab = page.locator(f'div.photo_type_div[data-sort-value="{tab_type}"]')
                if await tab.count() > 0 and await tab.first.is_visible():
                    await tab.first.click()
                    await asyncio.sleep(0.8)

                    # 클릭 후 해당 탭 아래 photo_box에서 data-origin 추출
                    photos = await page.eval_on_selector_all(
                        'div#photos_container .photo_box[data-origin]',
                        """elements => elements.map(el => ({
                            url: el.getAttribute('data-origin'),
                            nickname: el.getAttribute('data-nickname') || '',
                            date: el.getAttribute('data-date') || ''
                        }))"""
                    )
                    all_photos[tab_type] = photos
                    logger.debug(f"Collected {len(photos)} photos from '{tab_type}' tab")
            except Exception as e:
                logger.debug(f"Photo tab '{tab_type}' collection failed: {e}")
                all_photos[tab_type] = []

        return all_photos

    async def collect(self, target_url: str, **kwargs) -> Dict[str, Any]:
        """개별 매장 프로필 페이지 수집 - 인터랙션 포함"""
        async with async_playwright() as p:
            browser, page = await self._get_page(p)
            try:
                await page.goto(target_url, wait_until="domcontentloaded", timeout=40000)
                
                # 데이터 렌더링 대기
                try:
                    await page.wait_for_selector('h1.tit', timeout=15000)
                except:
                    logger.warning("Timeout waiting for 'h1.tit'")

                # 지연 로딩 강제 활성화를 위한 스크롤
                for _ in range(3):
                    await page.evaluate("window.scrollBy(0, 1000)")
                    await asyncio.sleep(0.8)

                # === 인터랙션 1: 메뉴 더보기 클릭 ===
                await self._click_menu_more(page)

                # === 인터랙션 2: 평가 더보기 반복 클릭 ===
                await self._click_review_more(page)

                # === 인터랙션 3: 접힌 리뷰 본문 펼치기 ===
                await self._expand_review_contents(page)

                # === 인터랙션 4: 사진 탭별 이미지 수집 ===
                photo_data = await self._collect_photo_tabs(page)

                # 최종 HTML 스냅샷 (인터랙션 후 완전히 펼쳐진 상태)
                content = await page.content()

                return {
                    "raw_content": content,
                    "photo_data": photo_data,
                    "platform": self.get_platform_name(),
                    "url": target_url
                }
            except Exception as e:
                raise NetworkException(ReasonCode.TIMEOUT, "raw_collection", "html", str(e))
            finally:
                await browser.close()
