import requests
from typing import Dict, Any, Optional
from .base_collector import BaseCollector
from ..core.file_manager import logger

class HttpCollector(BaseCollector):
    """
    HTTP requests를 사용하여 원시 HTML/JSON 데이터를 수집합니다.
    """
    
    def _get_headers(self) -> Dict[str, str]:
        return {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

    def collect(self, url: str) -> Dict[str, Any]:
        import time
        logger.info(f"--- [Collector] Collecting from URL: {url}")
        try:
            response = requests.get(url, headers=self._get_headers(), timeout=10)
            response.raise_for_status()
            
            # 인코딩 교정 (한글 깨짐 방지)
            if response.encoding == 'ISO-8859-1':
                response.encoding = response.apparent_encoding or 'utf-8'
            
            return {
                "status": "success",
                "raw_content": response.text,
                "http_status": response.status_code,
                "url": url,
                "collected_at": time.strftime("%Y-%m-%d %H:%M:%S") # Note: need to import time or use datetime
            }
        except Exception as e:
            logger.error(f"!!! [Collector] Failed to collect from {url}: {e}")
            return {
                "status": "fail",
                "reason_code": "NETWORK_ERROR",
                "reason_detail": str(e),
                "url": url
            }
