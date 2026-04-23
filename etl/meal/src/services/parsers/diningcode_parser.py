from bs4 import BeautifulSoup
from typing import Dict, Any, List
from src.services.parsers.base_parser import BaseParser
import re

class DiningCodeParser(BaseParser):
    """
    DiningCode 상세 페이지 파서.
    """
    
    def parse_shop(self, html: str) -> Dict[str, Any]:
        soup = BeautifulSoup(html, 'html.parser')
        
        # 기본 정보 추출 (샘플 셀렉터)
        title_tag = soup.select_one('div.tit')
        name = title_tag.get_text(strip=True) if title_tag else "Unknown"
        
        addr_tag = soup.select_one('li.locat')
        full_address = addr_tag.get_text(strip=True) if addr_tag else ""
        
        # DiningCode 고유 ID 추출 (URL 등에서 못 얻었을 경우를 대비해 스크립트 등 분석)
        internal_id = ""
        id_match = re.search(r'rid=(\d+)', html)
        if id_match:
            internal_id = id_match.group(1)
            
        return {
            "name": name,
            "full_address": full_address,
            "source_internal_id": internal_id,
            "source_platform": "DiningCode"
        }

    def parse_menus(self, html: str) -> List[Dict[str, Any]]:
        soup = BeautifulSoup(html, 'html.parser')
        menus = []
        
        # 메뉴 리스트 추출 (샘플 셀렉터)
        menu_items = soup.select('ul.menu-info > li')
        for item in menu_items:
            name_tag = item.select_one('span.nm')
            price_tag = item.select_one('span.pr')
            
            if name_tag:
                price_str = price_tag.get_text(strip=True).replace(',', '').replace('원', '') if price_tag else "0"
                try:
                    price = int(price_str)
                except ValueError:
                    price = 0
                    
                menus.append({
                    "name": name_tag.get_text(strip=True),
                    "price": price
                })
        return menus

    def parse_reviews(self, html: str) -> List[Dict[str, Any]]:
        soup = BeautifulSoup(html, 'html.parser')
        reviews = []
        
        # 리뷰 리스트 추출 (샘플 셀렉터)
        review_items = soup.select('div.p-comment')
        for item in review_items:
            content_tag = item.select_one('p.comment')
            author_tag = item.select_one('span.uname')
            
            if content_tag:
                reviews.append({
                    "content": content_tag.get_text(strip=True),
                    "author": author_tag.get_text(strip=True) if author_tag else "Anonymous",
                    "source_review_id": "" # 필요 시 추가 추출
                })
        return reviews
