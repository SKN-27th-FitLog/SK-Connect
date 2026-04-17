import json
import time
import re
from pathlib import Path
from typing import List, Dict, Set, Final, Optional
from playwright.sync_api import Page, Locator
import pandas as pd
from ..core.base_crawler import BaseCrawler
from ..core.file_manager import logger, file_manager

class ReviewExtractor(BaseCrawler):
    """
    다이닝코드 식당 상세 페이지에서 리뷰 데이터를 수집합니다.
    """
    
    RATING_PATTERN: Final[re.Pattern] = re.compile(r"[0-5](?:\.\d)?")

    def __init__(self, headless: bool = True):
        super().__init__(headless=headless)

    def _scroll_reviews(self, page: Page, rounds: int = 5):
        """'평가 더보기' 버튼 클릭 및 스크롤로 리뷰를 로드합니다."""
        try:
            more_btn = page.locator("a:has-text('평가 더보기')")
            if more_btn.count() > 0:
                more_btn.first.click(timeout=3000)
                page.wait_for_timeout(1000)
        except Exception:
            pass

        for _ in range(rounds):
            try:
                page.mouse.wheel(0, 4000)
                page.wait_for_timeout(800)
            except Exception:
                break

    def _collect_structured_reviews(self, page: Page, max_items: int = 500) -> List[Dict[str, object]]:
        """현재 페이지의 리뷰 블록에서 정형화된 데이터를 추출합니다."""
        reviews: List[Dict[str, object]] = []
        
        try:
            more_links = page.locator("a:has-text('...더보기')")
            for j in range(more_links.count()):
                try: more_links.nth(j).click(timeout=500)
                except: pass
        except: pass

        blocks = page.locator("div[id^='div_review_']")
        count = min(blocks.count(), max_items)

        for i in range(count):
            try:
                block = blocks.nth(i)
                review_id = block.get_attribute("id") or ""
                
                rating_text = ""
                for selector in [".star-point", "span.point", "p.person-grade"]:
                    loc = block.locator(selector)
                    if loc.count() > 0:
                        rating_text = self.safe_text(loc)
                        if rating_text: break
                rating = float(self.RATING_PATTERN.search(rating_text).group()) if self.RATING_PATTERN.search(rating_text) else 0.0
                
                date_text = ""
                for selector in [".date", "span.date", ".person-conf .date"]:
                    loc = block.locator(selector)
                    if loc.count() > 0:
                        date_text = self.safe_text(loc)
                        if date_text: break
                
                content = self.safe_text(block.locator(".review_contents, p.review_contents"))
                if not content: continue

                # 이미지 URL 추출
                img_locators = block.locator("img.review_img, .img_box img")
                image_urls: List[str] = []
                for idx in range(min(img_locators.count(), 10)):
                    src = img_locators.nth(idx).get_attribute("src")
                    if src and src.startswith("http"):
                        image_urls.append(src)

                reviews.append({
                    "review_id": review_id,
                    "rating": rating,
                    "date_text": date_text,
                    "content": content,
                    "image_urls": json.dumps(image_urls, ensure_ascii=False)
                })
            except Exception:
                continue
        return reviews

    def download_review_images(self, store_name: str, image_urls_json: str) -> List[str]:
        """리뷰 이미지들을 다운로드합니다."""
        try: urls = json.loads(image_urls_json)
        except: return []
        
        local_paths = []
        for url in urls:
            path = file_manager.download_image(url, store_name, prefix="rev")
            if path: local_paths.append(path)
        return local_paths

    def extract_reviews(self, store_url: str, store_name: str) -> List[Dict[str, object]]:
        """식당 상세 페이지에서 리뷰를 수집합니다."""
        def run_task(page: Page):
            logger.info(f"--- 리뷰 수집 중: {store_name}")
            try:
                page.goto(store_url, wait_until="domcontentloaded", timeout=60000)
                page.wait_for_timeout(1000)
                self._scroll_reviews(page)
                
                reviews = self._collect_structured_reviews(page)
                for rv in reviews:
                    local_imgs = self.download_review_images(store_name, rv["image_urls"])
                    rv.update({
                        "store_name": store_name,
                        "store_url": store_url,
                        "local_image_paths": json.dumps(local_imgs, ensure_ascii=False)
                    })
                return reviews
            except Exception as e:
                logger.error(f"!!! 리뷰 수집 실패 ({store_name}): {e}")
                return []
        
        return self.run(run_task)
