import random
import time
from typing import Optional, List, Dict, Final, Any
from playwright.sync_api import sync_playwright, Page, Browser, BrowserContext, Locator
from .file_manager import logger

class BaseCrawler:
    """
    모든 크롤러의 기반이 되는 클래스입니다.
    브라우저 컨텍스트 관리 및 공통 유틸리티(Anti-bot, Logging)를 제공합니다.
    """
    
    def __init__(self, headless: bool = True, slow_mo: int = 500):
        self.headless = headless
        self.slow_mo = slow_mo
        self._playwright = None
        self._browser = None
        self._context = None
        self.user_agent = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
        )

    def start(self):
        """브라우저를 시작하고 컨텍스트를 초기화합니다."""
        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(
            headless=self.headless, 
            slow_mo=self.slow_mo
        )
        self._context = self._browser.new_context(
            user_agent=self.user_agent,
            locale="ko-KR",
            viewport={"width": 1440, "height": 900}
        )
        logger.info(f"--- 브라우저 세션 시작 (Headless={self.headless})")
        return self._context.new_page()

    def stop(self):
        """브라우저 세션을 안전하게 종료합니다."""
        if self._browser:
            self._browser.close()
        if self._playwright:
            self._playwright.stop()
        logger.info("--- 브라우저 세션 종료")

    def pause(self, a: float = 1.0, b: float = 2.0):
        """사람의 행동처럼 보이도록 랜덤하게 대기합니다."""
        time.sleep(random.uniform(a, b))

    def safe_text(self, locator: Locator, default: str = "") -> str:
        """에러 없이 안전하게 텍스트를 추출합니다. (첫 번째 요소 기준)"""
        try:
            return locator.first.inner_text().strip()
        except Exception:
            return default

    def safe_attr(self, locator: Locator, attr: str, default: str = "") -> str:
        """에러 없이 안전하게 속성값을 추출합니다."""
        try:
            return locator.get_attribute(attr) or default
        except Exception:
            return default

    def scroll_to_bottom(self, page: Page, distance: int = 2000, rounds: int = 3):
        """페이지를 아래로 스크롤합니다."""
        for _ in range(rounds):
            page.mouse.wheel(0, distance)
            self.pause(0.5, 1.0)

    def run(self, task_fn):
        """
        브라우저 시작, 작업 수행, 종료 과정을 한 번에 관리합니다.
        task_fn: Page 객체를 인자로 받는 함수
        """
        page = self.start()
        try:
            return task_fn(page)
        finally:
            self.stop()
