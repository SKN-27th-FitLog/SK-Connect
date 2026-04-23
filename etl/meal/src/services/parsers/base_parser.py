from abc import ABC, abstractmethod
from typing import Dict, Any, List

class BaseParser(ABC):
    """
    설계안 9.4 준수 - 플랫폼별 파서 인터페이스.
    플랫폼마다 다른 HTML 구조를 분석하여 표준 Dict 구조로 반환.
    """
    
    @abstractmethod
    def parse_shop(self, html: str) -> Dict[str, Any]:
        """매장 정보 파싱"""
        pass

    @abstractmethod
    def parse_menus(self, html: str) -> List[Dict[str, Any]]:
        """메뉴 목록 파싱"""
        pass

    @abstractmethod
    def parse_reviews(self, html: str) -> List[Dict[str, Any]]:
        """리뷰 목록 파싱"""
        pass
