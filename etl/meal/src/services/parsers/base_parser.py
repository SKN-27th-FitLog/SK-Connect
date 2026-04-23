from abc import ABC, abstractmethod
from typing import Dict, Any, List

class BaseParser(ABC):
    """
    설계안 13장 준수 - 파서 기본 인터페이스.
    모든 플랫폼 파서는 이 클래스를 상속받아 정해진 규격의 데이터를 반환해야 함.
    """
    
    @abstractmethod
    def parse_shop(self, html: str) -> Dict[str, Any]:
        """매장 기본 정보 추출 (name, full_address, telephone, etc.)"""
        pass

    @abstractmethod
    def parse_menus(self, html: str) -> List[Dict[str, Any]]:
        """메뉴 목록 추출 (name, price)"""
        pass

    @abstractmethod
    def parse_reviews(self, html: str) -> List[Dict[str, Any]]:
        """리뷰 목록 추출 (content, author, rating, keywords)"""
        pass

    @abstractmethod
    def parse_images(self, html: str) -> List[str]:
        """이미지 URL 목록 추출"""
        pass
