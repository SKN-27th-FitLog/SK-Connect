from bs4 import BeautifulSoup
from typing import Dict, Any, List
from src.services.parsers.base_parser import BaseParser

class GoogleParser(BaseParser):
    def parse_shop(self, html: str) -> Dict[str, Any]:
        soup = BeautifulSoup(html, 'html.parser')
        # 구글 특화 셀렉터 기반 파싱
        name = soup.select_one('.DUwDbe') or soup.select_one('h1')
        return {
            "name": name.text if name else "Unknown", 
            "source_platform": "Google"
        }
    def parse_menus(self, html: str) -> List[Dict[str, Any]]: return []
    def parse_reviews(self, html: str) -> List[Dict[str, Any]]: return []
    def parse_images(self, html: str) -> List[str]: return []
