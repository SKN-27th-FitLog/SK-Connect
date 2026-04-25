from src.collectors.base_collector import BaseCollector
from src.core.policy.exceptions import NetworkException
from src.core.policy.reason_code import ReasonCode
from playwright.async_api import async_playwright
from typing import Dict, Any

class KakaoCollector(BaseCollector):
    """
    카카오 맵 특화 수집기.
    """
    def get_platform_name(self) -> str:
        return "Kakao"

    async def collect(self, target_url: str, **kwargs) -> Dict[str, Any]:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            try:
                response = await page.goto(target_url, wait_until="networkidle", timeout=30000)
                if not response or response.status != 200:
                    raise NetworkException(ReasonCode.NETWORK_ERROR, "raw_collection", "html", f"Kakao status {response.status}")
                return {
                    "raw_content": await page.content(),
                    "platform": self.get_platform_name(),
                    "url": target_url
                }
            finally:
                await browser.close()
