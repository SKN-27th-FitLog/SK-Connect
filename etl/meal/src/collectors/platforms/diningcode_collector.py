from src.collectors.base_collector import BaseCollector
from src.core.policy.exceptions import NetworkException, ScraperException
from src.core.policy.reason_code import ReasonCode
from playwright.async_api import async_playwright
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class DiningCodeCollector(BaseCollector):
    """
    DiningCode 전문 수집기.
    """
    
    def get_platform_name(self) -> str:
        return "DiningCode"

    async def collect(self, target_url: str, **kwargs) -> Dict[str, Any]:
        """
        Playwright를 사용하여 DiningCode 상세 페이지 HTML 수집.
        """
        async with async_playwright() as p:
            # 브라우저 실행 옵션 (설계안 21.2 고려)
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = await context.new_page()
            
            try:
                # 타임아웃 및 네트워크 상태 처리
                response = await page.goto(target_url, wait_until="networkidle", timeout=30000)
                
                if not response:
                    raise NetworkException(
                        ReasonCode.TIMEOUT, "raw_collection", "html", f"No response from {target_url}"
                    )
                
                if response.status == 404:
                    raise NetworkException(
                        ReasonCode.NOT_FOUND, "raw_collection", "html", f"Page not found: {target_url}"
                    )
                
                if response.status != 200:
                    raise NetworkException(
                        ReasonCode.NETWORK_ERROR, "raw_collection", "html", f"Status {response.status}: {target_url}"
                    )

                # 봇 감지 우회 여부 체크 (간단한 예시)
                content = await page.content()
                if "봇 감지" in content or "Captcha" in content:
                    raise NetworkException(
                        ReasonCode.BOT_DETECTED, "raw_collection", "html", f"Bot detected at {target_url}"
                    )

                return {
                    "raw_content": content,
                    "platform": self.get_platform_name(),
                    "url": target_url,
                    "collected_at": None # 필요 시 주입
                }

            except Exception as e:
                if isinstance(e, NetworkException):
                    raise
                # 일반적인 에러는 TIMEOUT 또는 NETWORK_ERROR로 분류
                raise NetworkException(
                    ReasonCode.TIMEOUT, "raw_collection", "html", str(e)
                )
            finally:
                await browser.close()
