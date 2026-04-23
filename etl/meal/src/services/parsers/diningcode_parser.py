from bs4 import BeautifulSoup
from typing import Dict, Any, List
from src.services.parsers.base_parser import BaseParser
from datetime import datetime
import re
import json
import logging
import urllib.parse

logger = logging.getLogger(__name__)

class DiningCodeParser(BaseParser):
    """
    다이닝코드 특화 파서.
    크롤링.txt 실제 HTML 구조 기반 셀렉터 적용.
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

    def _parse_price_text(self, text: str) -> int:
        """가격 문자열에서 숫자만 추출 (예: '5,500원' -> 5500)"""
        if not text:
            return 0
        digits = re.sub(r'[^\d]', '', text)
        return int(digits) if digits else 0

    def parse_shop(self, html: str) -> Dict[str, Any]:
        soup = BeautifulSoup(html, 'html.parser')
        ld_data = self._extract_json_ld(soup)
        
        # 1. 매장명: h1.tit
        name_tag = soup.select_one('h1.tit')
        name = name_tag.get_text(strip=True) if name_tag else ld_data.get('name', 'Unknown')
        
        # 2. 카테고리: a.btxt.category-0, a.btxt.category-1
        categories = []
        for cat_tag in soup.select('a.btxt[class*="category-"]'):
            cat_text = cat_tag.get_text(strip=True)
            if cat_text:
                categories.append(cat_text)
        
        # 3. 평점: #lbl_review_point > strong 또는 JSON-LD
        rating_val = 0.0
        rating_tag = soup.select_one('#lbl_review_point')
        if rating_tag:
            match = re.search(r'([\d\.]+)', rating_tag.get_text(strip=True))
            if match:
                rating_val = float(match.group(1))
        if rating_val == 0.0:
            agg_rating = ld_data.get('aggregateRating', {})
            if agg_rating:
                rating_val = float(agg_rating.get('ratingValue', 0))

        # 4. 주소: li.loc 내 a + span 조합 또는 JSON-LD
        full_address = ''
        # 주소 링크에서 도로명 주소 추출 (예: 서울특별시 금천구 시흥대로 315)
        addr_link = soup.select_one('li.locat a[href*="/list.dc"]')
        if addr_link:
            # 링크의 query 파라미터에서 주소 추출
            href = addr_link.get('href', '')
            query_match = re.search(r'query=(.+)', href)
            if query_match:
                addr_base = urllib.parse.unquote(query_match.group(1))
            else:
                addr_base = addr_link.get_text(strip=True)
            
            # 링크 뒤 span에서 상세 주소 추출
            addr_detail_span = addr_link.find_next_sibling('span')
            if not addr_detail_span:
                # li.locat 내부에서 span 찾기
                locat_li = soup.select_one('li.locat')
                if locat_li:
                    addr_detail_span = locat_li.select_one('span')
            
            addr_detail = addr_detail_span.get_text(strip=True) if addr_detail_span else ''
            full_address = f"{addr_base} {addr_detail}".strip()
        
        if not full_address:
            full_address = ld_data.get('address', {}).get('streetAddress', '')
        full_address = full_address.replace("지도보기", "").strip()
        
        # 5. 위경도 (JSON-LD 우선)
        geo = ld_data.get('geo', {})
        lat = float(geo.get('latitude', 0))
        lng = float(geo.get('longitude', 0))
        
        # 6. 전화번호: li.tel
        tel_tag = soup.select_one('li.tel')
        tel = tel_tag.get_text(strip=True) if tel_tag else ld_data.get('telephone', '')
        
        # 7. 설명 (메타태그)
        desc_meta = soup.find('meta', attrs={'name': 'description'})
        description = desc_meta.get('content', '') if desc_meta else ''

        # 8. 태그/특성 키워드: li.char 내 a 태그들
        char_keywords = []
        char_li = soup.select_one('li.char')
        if char_li:
            for a_tag in char_li.select('a'):
                kw = a_tag.get_text(strip=True)
                if kw:
                    char_keywords.append(kw)

        # 9. 영업시간
        business_hours = self._parse_business_hours(soup)

        # 10. 리뷰 건수
        review_count_tag = soup.select_one('.review-count')
        review_count = 0
        if review_count_tag:
            count_match = re.search(r'(\d+)', review_count_tag.get_text(strip=True))
            if count_match:
                review_count = int(count_match.group(1))

        # 11. 평가 분포 (5점~1점 각 건수)
        score_distribution = self._parse_score_distribution(soup)

        # 12. 세부 평점 (맛/가격/응대)
        detail_evaluation = self._parse_detail_evaluation(soup)

        # 13. 키워드 통계 (용도/주차/분위기)
        keyword_stats = self._parse_keyword_stats(soup)

        # 14. ID 추출 (URL 및 메타태그에서)
        rid_match = re.search(r'rid=([a-zA-Z0-9\-_]+)', html)
        rid = rid_match.group(1) if rid_match else ""

        return {
            "name": name,
            "categories": categories,
            "description": description,
            "full_address": full_address,
            "telephone": tel,
            "latitude": lat,
            "longitude": lng,
            "rating": rating_val,
            "review_count": review_count,
            "char_keywords": char_keywords,
            "business_hours": business_hours,
            "score_distribution": score_distribution,
            "detail_evaluation": detail_evaluation,
            "keyword_stats": keyword_stats,
            "source_internal_id": rid,
            "source_platform": "DiningCode",
            "canonical_url": f"https://www.diningcode.com/profile.php?rid={rid}" if rid else ""
        }

    def _parse_business_hours(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """영업시간 정보 추출"""
        result = {
            "status": "",
            "today_hours": "",
            "weekly": []
        }
        
        # 영업 상태
        status_tag = soup.select_one('.open-status')
        if status_tag:
            result["status"] = status_tag.get_text(strip=True)
        
        # 오늘 영업시간
        today_tag = soup.select_one('#today-main-hours')
        if today_tag:
            result["today_hours"] = today_tag.get_text(strip=True)
        
        # 주간 영업시간
        dates = soup.select('.hour_date')
        times = soup.select('.hour_time')
        for date_tag, time_tag in zip(dates, times):
            date_text = date_tag.get_text(strip=True)
            time_text = time_tag.get_text(strip=True)
            is_closed = 'closed' in (time_tag.get('class', []) if isinstance(time_tag.get('class'), list) else [])
            result["weekly"].append({
                "date": date_text,
                "hours": time_text,
                "is_closed": is_closed
            })
        
        return result

    def _parse_score_distribution(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """평점별 분포 추출 (5점~1점 건수)"""
        distribution = []
        for li in soup.select('ul.app-graph li'):
            score_tag = li.select_one('.score-number')
            label_tag = li.select_one('p.btxt')
            count_tag = li.select_one('p.score-count')
            if score_tag and count_tag:
                count_text = count_tag.get_text(strip=True)
                count_match = re.search(r'(\d+)', count_text)
                distribution.append({
                    "score": float(score_tag.get_text(strip=True)),
                    "label": label_tag.get_text(strip=True) if label_tag else "",
                    "count": int(count_match.group(1)) if count_match else 0
                })
        return distribution

    def _parse_detail_evaluation(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """세부 평가 (맛/가격/응대) 추출"""
        evaluations = []
        for item in soup.select('.detail-evaluation .eval-item'):
            name_tag = item.select_one('.category-name')
            score_tag = item.select_one('.category-score')
            if name_tag and score_tag:
                # 세부 바 정보
                bars = []
                for bar in item.select('.eval-bar-item'):
                    label_tag = bar.select_one('.bar-label')
                    percent_tag = bar.select_one('.bar-percent')
                    if label_tag and percent_tag:
                        bars.append({
                            "label": label_tag.get_text(strip=True),
                            "percent": percent_tag.get_text(strip=True)
                        })
                evaluations.append({
                    "category": name_tag.get_text(strip=True),
                    "score": float(score_tag.get_text(strip=True)),
                    "details": bars
                })
        return evaluations

    def _parse_keyword_stats(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """키워드 통계 (용도/주차/분위기 등) 추출"""
        keyword_groups = []
        for preview in soup.select('p.cate[id^="keyword_preview_"]'):
            group_index = preview.get('data-index', '')
            keywords = []
            for span in preview.select('span'):
                text = span.get_text(strip=True)
                # "키워드명 숫자" 형태에서 분리
                b_tag = span.select_one('b')
                if b_tag:
                    count = int(b_tag.get_text(strip=True))
                    keyword_name = text.replace(b_tag.get_text(), '').strip()
                    keywords.append({"keyword": keyword_name, "count": count})
            if keywords:
                keyword_groups.append({
                    "group_index": group_index,
                    "keywords": keywords
                })
        return keyword_groups

    def parse_menus(self, html: str) -> List[Dict[str, Any]]:
        """메뉴 목록 추출 - 크롤링.txt 실제 셀렉터 기반"""
        soup = BeautifulSoup(html, 'html.parser')
        menus = []
        
        # ul.Restaurant-MenuList 내 li 항목
        menu_items = soup.select('ul.Restaurant-MenuList li[data-menu-index]')
        for item in menu_items:
            name_tag = item.select_one('span.restaurant-menu')
            price_tag = item.select_one('p.restaurant-price')
            desc_tag = item.select_one('p.menu-description')
            
            if name_tag:
                menu_name = name_tag.get_text(strip=True)
                price_text = price_tag.get_text(strip=True) if price_tag else "0"
                price = self._parse_price_text(price_text)
                description = desc_tag.get_text(strip=True) if desc_tag else ""
                
                menus.append({
                    "name": menu_name,
                    "price": price,
                    "description": description,
                    "menu_index": item.get('data-menu-index', '')
                })
        return menus

    def parse_reviews(self, html: str) -> List[Dict[str, Any]]:
        """리뷰 목록 추출 - 크롤링.txt 실제 셀렉터 기반"""
        soup = BeautifulSoup(html, 'html.parser')
        reviews = []
        
        # 리뷰 컨테이너: div.latter-graph-body
        review_items = soup.select('div.latter-graph-body')
        
        for item in review_items:
            # 작성자: .person-grade strong
            author_tag = item.select_one('.person-grade strong')
            if not author_tag:
                continue
            author = author_tag.get_text(strip=True)

            # 작성자 통계 (평균별점, 평가수, 팔로워)
            avg_score_tag = item.select_one('.avg_score')
            rv_cnt_tag = item.select_one('.rv_cnt')
            follower_cnt_tag = item.select_one('.follower_cnt')
            
            author_stats = {
                "avg_score": float(avg_score_tag.get_text(strip=True)) if avg_score_tag else 0.0,
                "review_count": int(rv_cnt_tag.get_text(strip=True)) if rv_cnt_tag else 0,
                "follower_count": int(follower_cnt_tag.get_text(strip=True)) if follower_cnt_tag else 0
            }

            # 별점: .total_score (예: "4.5점")
            rating = 0.0
            score_tag = item.select_one('.total_score')
            if score_tag:
                match = re.search(r'([\d\.]+)', score_tag.get_text(strip=True))
                if match:
                    rating = float(match.group(1))

            # 작성일: .date span
            visited_at = ""
            date_tag = item.select_one('span.date')
            if date_tag:
                visited_at = date_tag.get_text(strip=True)

            # 리뷰 본문: div.review_contents.btxt
            content = ""
            content_tag = item.select_one('div.review_contents.btxt')
            if content_tag:
                # <br> 태그를 줄바꿈으로 변환
                for br in content_tag.find_all('br'):
                    br.replace_with('\n')
                content = content_tag.get_text(strip=True)

            # 세부 평가 (맛/가격/응대): .sub_title .text
            sub_evaluations = {}
            for sub in item.select('.sub_title'):
                full_text = sub.get_text(strip=True)
                text_tag = sub.select_one('.text')
                if text_tag:
                    value = text_tag.get_text(strip=True)
                    # "맛: " 부분 추출
                    category = full_text.replace(value, '').replace(':', '').strip()
                    sub_evaluations[category] = value

            # 주문한 메뉴: .ordered_menu_list
            ordered_menus = []
            ordered_tag = item.select_one('.ordered_menu_list')
            if ordered_tag:
                ordered_text = ordered_tag.get_text(strip=True)
                ordered_menus = [m.strip() for m in ordered_text.split(',') if m.strip()]

            # 리뷰 키워드: .new-keyword_list
            keywords = []
            keyword_tag = item.select_one('.new-keyword_list')
            if keyword_tag:
                kw_text = keyword_tag.get_text(strip=True)
                keywords = [k.strip() for k in kw_text.split(',') if k.strip()]

            # 리뷰 사진: .btn-gallery-review[data-origin]
            review_images = []
            for img_div in item.select('.btn-gallery-review[data-origin]'):
                origin_url = img_div.get('data-origin', '')
                if origin_url:
                    review_images.append(origin_url)

            reviews.append({
                "content": content,
                "author": author,
                "author_stats": author_stats,
                "visited_at": visited_at,
                "rating": rating,
                "sub_evaluations": sub_evaluations,
                "ordered_menus": ordered_menus,
                "keywords": keywords,
                "review_images": review_images,
                "source_review_id": ""
            })
        return reviews

    def parse_images(self, html: str, photo_data: Dict[str, List] = None) -> List[Dict[str, Any]]:
        """
        이미지 URL 목록 추출.
        photo_data가 있으면 컬렉터에서 탭별로 수집한 데이터 사용,
        없으면 HTML에서 직접 추출.
        """
        images = []

        # 1. 컬렉터에서 탭별 수집된 데이터 우선
        if photo_data:
            for category, photos in photo_data.items():
                for photo in photos:
                    url = photo.get('url', '') if isinstance(photo, dict) else photo
                    if url and url.startswith('http'):
                        images.append({
                            "url": url,
                            "category": category,
                            "nickname": photo.get('nickname', '') if isinstance(photo, dict) else '',
                            "date": photo.get('date', '') if isinstance(photo, dict) else ''
                        })
            if images:
                # URL 기준 중복 제거
                seen = set()
                unique = []
                for img in images:
                    if img["url"] not in seen:
                        seen.add(img["url"])
                        unique.append(img)
                return unique

        # 2. HTML 폴백: photo_box의 data-origin 속성에서 추출
        soup = BeautifulSoup(html, 'html.parser')
        seen_urls = set()
        for photo_box in soup.select('.photo_box[data-origin]'):
            url = photo_box.get('data-origin', '')
            nickname = photo_box.get('data-nickname', '')
            date = photo_box.get('data-date', '')
            if url and url.startswith('http') and url not in seen_urls:
                seen_urls.add(url)
                images.append({
                    "url": url,
                    "category": "unknown",
                    "nickname": nickname,
                    "date": date
                })

        return images
