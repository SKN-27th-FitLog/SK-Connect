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

            return {
                "status": "success",
                "source_platform": "diningcode",
                "source_internal_id": internal_id,
                "name": name,
                "address": address,
                "latitude": lat,
                "longitude": lng,
                "rating": rating,
                "category_cd": "CA01", # TODO: category_str를 코드로 변환하는 Mapper 필요
                "address_cd": "CA01",  # TODO: address를 코드로 변환하는 Mapper 필요
                "canonical_url": url,
                "extracted_at": datetime.now().isoformat(),
                "menus": [],
                "reviews": []
            }
            
        except Exception as e:
            logger.error(f"!!! [Parser] Unexpected parsing failed: {e}")
            return {
                "status": "fail",
                "reason_code": "UNKNOWN_PARSING_ERROR",
                "reason_detail": str(e)
            }
