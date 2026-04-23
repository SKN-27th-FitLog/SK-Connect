import re
import json
from bs4 import BeautifulSoup
from typing import Dict, Any, Optional
from datetime import datetime
from ..core.file_manager import logger

class StoreParser:
    """
    Stage 2: Candidate Parsing
    수집된 Raw HTML 등에서 매장 정보를 추출하여 Candidate 형태로 만듭니다.
    """
    
    def parse(self, raw_data: str, url: str = "unknown") -> Dict[str, Any]:
        """
        HTML 파싱을 통해 정보를 추출합니다.
        실제 운영 환경에서는 복잡한 셀렉터와 예외 처리가 포함됩니다.
        """
        if not raw_data:
            return {"status": "fail", "reason_code": "EMPTY_RAW_DATA"}

        try:
            soup = BeautifulSoup(raw_data, "html.parser")
            
            # 1. JSON-LD 데이터 확인 (강력한 탐색 방식)
            json_ld = soup.find('script', type='application/ld+json')
            ld_data = {}
            if json_ld:
                try:
                    # string이 None일 경우 text 시도
                    content = json_ld.string or json_ld.get_text()
                    ld_data = json.loads(content)
                except:
                    pass

            # 2. 상호명 추출
            name = None
            if isinstance(ld_data, dict):
                name = ld_data.get("name")
            name = name or (soup.select_one(".tit, #title, h1.name").get_text(strip=True) if soup.select_one(".tit, #title, h1.name") else None)
            
            if not name:
                name = "알 수 없는 상호명"
            
            # 3. 주소 추출 (다각도 탐색)
            address = "주소 정보 없음"
            if isinstance(ld_data, dict) and "address" in ld_data:
                addr_obj = ld_data["address"]
                if isinstance(addr_obj, dict):
                    address = addr_obj.get("streetAddress") or addr_obj.get("addressLocality") or address
                else:
                    address = str(addr_obj)
            
            # JSON-LD 실패 시 비상용 Selector
            if address == "주소 정보 없음":
                addr_tag = soup.select_one(".addr, .address, li.addr, span.addr")
                if addr_tag:
                    address = addr_tag.get_text(strip=True)

            # 4. 좌표 추출 (Hidden Input 탐색)
            lat = 0.0
            lng = 0.0
            lat_tag = soup.select_one("#hdn_lat")
            lng_tag = soup.select_one("#hdn_lng")
            if lat_tag and lng_tag:
                try:
                    lat = float(lat_tag.get("value", 0.0))
                    lng = float(lng_tag.get("value", 0.0))
                except:
                    pass

            # 5. 플랫폼 ID 추출 (URL에서 rid 추출)
            internal_id = "unknown_id"
            rid_match = re.search(r"rid=([^&./]+)", url)
            if rid_match:
                internal_id = rid_match.group(1)

            # 6. 별점(Rating) 추출
            rating = 0.0
            try:
                if isinstance(ld_data, dict) and "aggregateRating" in ld_data:
                    r_val = ld_data["aggregateRating"].get("ratingValue")
                    if r_val:
                        rating = float(r_val)
                
                if rating == 0.0:
                    rt_tag = soup.select_one("#lbl_review_point, .point strong")
                    if rt_tag:
                        rating = float(rt_tag.get_text(strip=True))
            except Exception as e:
                logger.warning(f"--- [Parser] Rating extraction failed: {e}")
                rating = 0.0

            # 7. 카테고리 텍스트 추출 (코드 매핑 전 단계)
            category_str = "음식점"
            try:
                if isinstance(ld_data, dict) and "servesCuisine" in ld_data:
                    cuisine = ld_data["servesCuisine"]
                    category_str = cuisine[0] if isinstance(cuisine, list) else str(cuisine)
                else:
                    cat_tag = soup.select_one(".btxt.category-0, .category, .area-category")
                    if cat_tag:
                        category_str = cat_tag.get_text(strip=True)
            except:
                pass

            # 8. 메뉴 추출 (JSON-LD hasMenu)
            menus = []
            try:
                if isinstance(ld_data, dict) and "hasMenu" in ld_data:
                    menu_items = ld_data["hasMenu"].get("hasMenuItem", [])
                    for item in menu_items:
                        price_str = item.get("offers", {}).get("price", "0")
                        # "12,000원" → 12000
                        price_num = int(re.sub(r"[^\d]", "", str(price_str)) or 0)
                        menus.append({
                            "name": item.get("name", ""),
                            "price": price_num,
                            "description": None
                        })
            except Exception as e:
                logger.warning(f"--- [Parser] Menu extraction failed: {e}")

            # 9. 리뷰 추출 (HTML 블록 탐색)
            reviews = []
            try:
                # 다이닝코드 최신 리뷰 HTML 구조 (.latter-graph 또는 .near_review)
                review_blocks = soup.select(".latter-graph, .near_review, .person-review")
                
                for rv in review_blocks:
                    # 1) 작성자
                    author_tag = rv.select_one(".person-grade strong, .person-grade .btxt, .name")
                    author_id = author_tag.get_text(strip=True) if author_tag else None

                    # 2) 별점
                    rating_tag = rv.select_one(".total_score")
                    rv_rating = None
                    if rating_tag:
                        # "5점" -> 5.0
                        try:
                            rv_rating = float(rating_tag.get_text(strip=True).replace("점", ""))
                        except:
                            pass

                    # 3) 작성일
                    date_tag = rv.select_one("span.date")
                    date_published = date_tag.get_text(strip=True) if date_tag else None

                    # 4) 내용
                    content_tag = rv.select_one(".review_contents")
                    content = content_tag.get_text(" ", strip=True) if content_tag else ""

                    # 5) 평가 항목 (맛, 가격, 서비스)
                    taste_eval, price_eval, service_eval = None, None, None
                    sub_titles = rv.select(".sub_title")
                    for st in sub_titles:
                        sub_text = st.get_text(" ", strip=True)
                        if "맛:" in sub_text:
                            taste_eval = sub_text.replace("맛:", "").strip()
                        elif "가격:" in sub_text:
                            price_eval = sub_text.replace("가격:", "").strip()
                        elif "응대:" in sub_text or "서비스:" in sub_text:
                            service_eval = sub_text.replace("응대:", "").replace("서비스:", "").strip()

                    # 6) 주문한 메뉴
                    ordered_tag = rv.select_one(".ordered_menu_list")
                    ordered_menu = ordered_tag.get_text(strip=True) if ordered_tag else None

                    # 7) 키워드
                    keywords = []
                    keyword_tag = rv.select_one(".new-keyword_list")
                    if keyword_tag:
                        keywords = [k.strip() for k in keyword_tag.get_text(strip=True).split(",")]
                    else:
                        # 구버전 키워드 셀렉터 대비
                        old_tags = rv.select(".keyword span")
                        if old_tags:
                            keywords = [t.get_text(strip=True) for t in old_tags]

                    reviews.append({
                        "content": content,
                        "rating": rv_rating,
                        "author_id": author_id,
                        "date_published": date_published,
                        "ordered_menu": ordered_menu,
                        "keywords": keywords,
                        "taste_eval": taste_eval,
                        "price_eval": price_eval,
                        "service_eval": service_eval
                    })
            except Exception as e:
                logger.warning(f"--- [Parser] Review extraction failed: {e}")

            # 10. 이미지 URL 추출 (JSON-LD image)
            images = []
            try:
                if isinstance(ld_data, dict) and "image" in ld_data:
                    ld_images = ld_data["image"]
                    if isinstance(ld_images, str):
                        ld_images = [ld_images]
                    for img_url in ld_images:
                        if img_url and isinstance(img_url, str):
                            images.append({"image_url": img_url})
            except Exception as e:
                logger.warning(f"--- [Parser] Image extraction failed: {e}")

            return {
                "status": "success",
                "source_platform": "diningcode",
                "source_internal_id": internal_id,
                "name": name,
                "address": address,
                "latitude": lat,
                "longitude": lng,
                "rating": rating,
                "category_cd": "CA01",
                "address_cd": "CA01",
                "canonical_url": url,
                "extracted_at": datetime.now().isoformat(),
                "menus": menus,
                "reviews": reviews,
                "images": images
            }
            
        except Exception as e:
            logger.error(f"!!! [Parser] Unexpected parsing failed: {e}")
            return {
                "status": "fail",
                "reason_code": "UNKNOWN_PARSING_ERROR",
                "reason_detail": str(e)
            }
