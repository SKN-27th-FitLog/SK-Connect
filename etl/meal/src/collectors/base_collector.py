from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class BaseCollector(ABC):
    """
    모든 수집기의 기본 클래스입니다.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}

    @abstractmethod
    def collect(self, url: str) -> Dict[str, Any]:
        """
        URL로부터 데이터를 수집합니다.
        """
        pass

    def _get_headers(self) -> Dict[str, str]:
        return {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
