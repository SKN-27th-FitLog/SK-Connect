from bs4 import BeautifulSoup
from typing import Dict, Any, List
from src.services.parsers.base_parser import BaseParser
import re
import json
import logging

logger = logging.getLogger(__name__)

class DiningCodeParser(BaseParser):
    """
    다이닝코드 특화 파서.
    JSON-LD와 DOM 선택자를 병행하여 누락 없는 데이터 추출 보장.
    """
    
    def _extract_json_ld(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """LD+JSON 스크립트에서 정형 데이터 추출"""
        try:
            scripts = soup.find_all('script', type='application/ld+json')
            for script in scripts:
                data = json.loads(script.string)
                if data.get('@type') in ['Restaurant', 'FoodEstablishment']:
                    return data
        except Exception as e:
            logger.debug(f"JSON-LD extraction failed: {e}")
        return {}

    def parse_shop(self, html: str) -> Dict[str, Any]:
        soup = BeautifulSoup(html, 'html.parser')
        ld_data = self._extract_json_ld(soup)
        
        # 1. 기본 정보 (DOM 우선)
        name_tag = soup.select_one('div.tit-point')
        name = name_tag.get_text(strip=True) if name_tag else ld_data.get('name', 'Unknown')
        
        # 2. 주소 처리
        addr_tag = soup.select_one('li.loc p.addr')
        full_address = addr_tag.get_text(strip=True) if addr_tag else ld_data.get('address', {}).get('streetAddress', '')
        # "지도보기" 등 노이즈 제거
        full_address = full_address.replace("지도보기", "").strip()
        
        # 3. 위경도 (JSON-LD 우선)
        geo = ld_data.get('geo', {})
        lat = float(geo.get('latitude', 0))
        lng = float(geo.get('longitude', 0))
        
        # 4. 기타 정보
        tel_tag = soup.select_one('li.tel')
        tel = tel_tag.get_text(strip=True) if tel_tag else ld_data.get('telephone', '')
        
        # 설명 (메타태그 또는 태그)
        desc_meta = soup.find('meta', attrs={'name': 'description'})
        description = desc_meta.get('content', '') if desc_meta else ''

        # 평점 (LD-JSON 또는 DOM)
        rating_val = 0.0
        agg_rating = ld_data.get('aggregateRating', {})
        if agg_rating:
            rating_val = float(agg_rating.get('ratingValue', 0))
        else:
            # DOM에서 시도 (예: 4.5점)
            rating_tag = soup.select_one('span.star i + em')
            if rating_tag:
                match = re.search(r'([\d\.]+)', rating_tag.text)
                if match: rating_val = float(match.group(1))

        # ID 추출 (URL에서)
        rid_match = re.search(r'rid=([^&]+)', html)
        rid = rid_match.group(1) if rid_match else ""

        return {
            "name": name,
            "description": description,
            "full_address": full_address,
            "telephone": tel,
            "latitude": lat,
            "longitude": lng,
            "rating": rating_val,
            "source_internal_id": rid,
            "source_platform": "DiningCode",
            "canonical_url": f"https://www.diningcode.com/profile.php?rid={rid}" if rid else ""
        }

    def parse_menus(self, html: str) -> List[Dict[str, Any]]:
        soup = BeautifulSoup(html, 'html.parser')
        menus = []
        menu_items = soup.select('div.menu-info li')
        for item in menu_items:
            nm_tag = item.select_one('span.nm')
            pr_tag = item.select_one('span.pr')
            if nm_tag:
                price_text = pr_tag.get_text(strip=True) if pr_tag else "0"
                price = int(re.sub(r'[^\d]', '', price_text)) if price_text and any(c.isdigit() for c in price_text) else 0
                menus.append({
                    "name": nm_tag.get_text(strip=True),
                    "price": price
                })
        return menus

    def parse_reviews(self, html: str) -> List[Dict[str, Any]]:
        soup = BeautifulSoup(html, 'html.parser')
        reviews = []
        # 다이닝코드 리뷰는 n-review 또는 review-container
        review_items = soup.select('div.review-container, div.n-review') 
        # 실제로는 위 컨테이너 내부의 li 들임
        review_list = soup.select('div.review-container li, div.n-review li')
        
        for item in review_list:
            content_tag = item.select_one('p.review_contents')
            author_tag = item.select_one('span.uname')
            star_tag = item.select_one('span.star') # 내부의 em 등 확인 필요
            
            if content_tag and author_tag:
                # 평점 추출
                rating = 0.0
                if star_tag:
                    star_text = star_tag.get_text(strip=True)
                    match = re.search(r'([\d\.]+)', star_text)
                    if match: rating = float(match.group(1))
                
                # 키워드 추출
                keywords = []
                keyword_tag = item.select_one('p.keywords')
                if keyword_tag:
                    # "키워드" 텍스트 제거 후 콤마로 분리
                    kw_text = keyword_tag.get_text(strip=True).replace("키워드", "")
                    keywords = [k.strip() for k in kw_text.split(',') if k.strip()]

                reviews.append({
                    "content": content_tag.get_text(strip=True),
                    "author": author_tag.get_text(strip=True),
                    "visited_at": datetime.now().strftime("%Y-%m-%d"), # 일시 정보가 정확하지 않을 때 대비
                    "rating": rating,
                    "keywords": keywords,
                    "source_review_id": "" # 필요시 추가 추출
                })
        return reviews

    def parse_images(self, html: str) -> List[str]:
        soup = BeautifulSoup(html, 'html.parser')
        images = []
        # 상단 이미지 및 갤러리 이미지
        img_tags = soup.select('div.slick-track img, div.gallery img')
        for img in img_tags:
            src = img.get('src') or img.get('data-src')
            if src and src.startswith('http'):
                images.append(src)
        return list(dict.fromkeys(images)) # 중복 제거
from datetime import datetime
