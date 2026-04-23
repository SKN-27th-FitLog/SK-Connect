from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class BaseCollector(ABC):
    """
    설계안 9장 준수 - 플랫폼별 수집기 공통 인터페이스.
    Collector는 플랫폼 특화 수집(Raw)만 담당하며 정책 판단은 하지 않음.
    """
    
    @abstractmethod
    async def collect(self, target_url: str, **kwargs) -> Dict[str, Any]:
        """
        주어진 URL에서 데이터를 수집하여 Raw 결과를 반환.
        반환 규격: { "raw_content": str, "metadata": Dict, ... }
        """
        pass

    @abstractmethod
    def get_platform_name(self) -> str:
        """수집 플랫폼 명칭 반환 (Naver, DiningCode 등)"""
        pass
