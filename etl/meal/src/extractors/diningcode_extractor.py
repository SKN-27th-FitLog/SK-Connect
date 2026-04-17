import json
import re
import time
import requests
from typing import List, Dict, Final, Optional
from bs4 import BeautifulSoup
from playwright.sync_api import Page
from ..core.base_crawler import BaseCrawler
from ..core.file_manager import logger, file_manager

class DiningCodeExtractor(BaseCrawler):
    """
    다이닝코드 웹사이트에서 식당 상세 정보를 추출하는 초정밀 익스트래터입니다. (v3.6)
    - v3.5 이슈: 정적 추출 시 셀렉터 불일치(Meta 태그 부재 등)로 인한 실패.
    - v3.6 개선: JSON-LD 파싱 및 내부 Hidden Input(hdn_lat/lng) 기반 데이터 추출.
    """
    
    BASE_URL: Final[str] = "https://www.diningcode.com"
    RATING_PATTERN: Final[re.Pattern] = re.compile(r"[0-5](?:\.\d)?")
    USER_AGENT: Final[str] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, Gecko) Chrome/123.0.0.0 Safari/537.36"

    def __init__(self, headless: bool = True):
        super().__init__(headless=headless, slow_mo=1200)

    def extract_details(self, url: str, store_name: str) -> Dict[str, str]:
        """단일 매장 상세 정보를 수집합니다. (v3.6: JSON-LD King)"""
        result = {
            "store_name": store_name,
            "store_url": url,
            "status": "error",
            "error_message": "",
            "store_address": "",
            "store_rating": "0.0",
            "menus_json": "[]",
            "shop_image_urls": "[]",
            "latitude": "0.0",
            "longitude": "0.0",
            "source_category": ""
        }
        
        # [Step 1] Requests + JSON-LD 기반 정적 데이터 확보 (가장 확실함)
        try:
            logger.info(f"--- [v3.6/Static] 정적 데이터(JSON-LD) 추출 시작: {store_name}")
            resp = requests.get(url, headers={"User-Agent": self.USER_AGENT}, timeout=15)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, 'html.parser')
                
                # 1. JSON-LD 파싱 (이름, 주소, 평점, 기본메뉴가 다 들어있음)
                ld_json_tag = soup.find("script", type="application/ld+json")
                if ld_json_tag:
                    try:
                        ld_data = json.loads(ld_json_tag.get_text())
                        result["store_address"] = ld_data.get("address", {}).get("streetAddress", "")
                        result["store_rating"] = str(ld_data.get("aggregateRating", {}).get("ratingValue", "0.0"))
                        
                        # 메뉴 추출 (JSON-LD 구조)
                        ld_menus = []
                        menu_obj = ld_data.get("hasMenu", {})
                        if menu_obj:
                            items = menu_obj.get("hasMenuItem", [])
                            for it in items:
                                m_n = it.get("name", "")
                                m_p = it.get("offers", {}).get("price", "")
                                if m_n: ld_menus.append({"menu_name": m_n, "menu_price": m_p})
                        
                        # servesCuisine 필드에도 메뉴 정보가 있는 경우 보완
                        cuisine = ld_data.get("servesCuisine", [])
                        if isinstance(cuisine, list):
                            for c in cuisine:
                                if " - " in c:
                                    n, p = c.split(" - ", 1)
                                    if n not in [m["menu_name"] for m in ld_menus]:
                                        ld_menus.append({"menu_name": n.strip(), "menu_price": p.strip()})
                        
                        result["menus_json"] = json.dumps(ld_menus, ensure_ascii=False)
                    except Exception as je:
                        logger.warning(f"JSON-LD 파싱 실패: {je}")

                # 2. 좌표 추출 (Hidden Inputs)
                lat_input = soup.select_one("#hdn_lat")
                lon_input = soup.select_one("#hdn_lng")
                if lat_input: result["latitude"] = lat_input.get("value", "0.0")
                if lon_input: result["longitude"] = lon_input.get("value", "0.0")

                logger.info(f"--- [v3.6/Static] 추출 성공: 좌표({result['latitude']}), 메뉴({len(json.loads(result['menus_json']))}건)")
        except Exception as e:
            logger.warning(f"--- [v3.6/Static] 정적 추출 실패: {e}")

        # [Step 2] Playwright 동적 데이터 보완 (이미지 중심)
        if result["status"] != "ok": # 기본적으로 정적 데이터만으로도 ok 가능하나 이미지를 위해 진행
            try:
                logger.info(f"--- [v3.6/Dynamic] 동적 이미지 보완 시작: {store_name}")
                page = self.start()
                page.goto(url, wait_until="networkidle", timeout=45000)
                page.wait_for_timeout(2000)
                
                dynamic_data = page.evaluate("""
                    () => {
                        const imgs = Array.from(document.querySelectorAll('.carousel-item img, .pic-list img, .photo_type_div img, .title-img img'));
                        const imageUrls = [...new Set(imgs.map(img => img.src))].filter(src => src && src.startsWith('http')).slice(0, 10);
                        return { imageUrls };
                    }
                """)
                result["shop_image_urls"] = json.dumps(dynamic_data["imageUrls"], ensure_ascii=False)
                
                # 주소와 위경도가 채워졌다면 성공 처리
                if result["store_address"] and result["latitude"] != "0.0":
                    result["status"] = "ok"
            except Exception as e:
                logger.error(f"--- [v3.6/Dynamic] 보완 실패: {e}")
                if result["store_address"] and result["latitude"] != "0.0":
                    result["status"] = "ok"
            finally:
                self.stop()
            
        return result

    def batch_extract_details(self, candidates: List[Dict[str, str]], limit: Optional[int] = None):
        results = []
        target_list = candidates[:limit] if limit else candidates
        for item in target_list:
            res = self.extract_details(item.get("store_url"), item.get("store_name"))
            res.update({"source_region": item.get("source_region", ""), "source_category": item.get("source_category", "")})
            results.append(res)
        return results
