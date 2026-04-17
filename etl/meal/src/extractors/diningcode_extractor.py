import json
import re
import time
from typing import List, Dict, Final, Optional
from playwright.sync_api import Page
from ..core.base_crawler import BaseCrawler
from ..core.file_manager import logger, file_manager

class DiningCodeExtractor(BaseCrawler):
    """
    다이닝코드 웹사이트에서 식당 상세 정보를 추출하는 익스트래터입니다.
    """
    
    BASE_URL: Final[str] = "https://www.diningcode.com"
    RATING_PATTERN: Final[re.Pattern] = re.compile(r"[0-5](?:\.\d)?")

    def __init__(self, headless: bool = True):
        super().__init__(headless=headless)

    def extract_details(self, url: str, store_name: str) -> Dict[str, str]:
        """단일 매장 상세 정보를 수집합니다."""
        page = self.start()
        result = {
            "store_name": store_name,
            "store_url": url,
            "status": "error",
            "error_message": "",
            "store_address": "",
            "store_rating": "0.0",
            "menus_json": "[]",
            "source_category": ""
        }
        
        try:
            logger.info(f"--- 상세 수집 시작: {store_name} ({url})")
            logger.info("--- 페이지 이동 중...")
            response = page.goto(url, wait_until="domcontentloaded", timeout=45000)
            logger.info(f"--- 페이지 이동 완료 (Status: {response.status if response else 'N/A'})")
            
            # 동적 컨텐츠 렌더링 및 필수 요소 대기
            try:
                page.wait_for_selector(".star-point, span.point", timeout=10000)
            except Exception:
                logger.warning("--- 필수 요소 로딩 대기 제한 시간 초과")

            # 데이터 추출
            data = page.evaluate("""
                () => {
                    const safeText = (sel) => {
                        const el = document.querySelector(sel);
                        return el ? el.innerText.trim() : "";
                    };
                    
                    let addr = safeText('li.loc');
                    if (!addr) addr = safeText('.address');
                    if (!addr) {
                        // '지번' 혹은 '위치' 근처의 텍스트 찾기 시도
                        const locIconEl = Array.from(document.querySelectorAll('i')).find(i => i.innerText.includes('location') || i.className.includes('loc'));
                        if (locIconEl && locIconEl.parentElement) addr = locIconEl.parentElement.innerText.trim();
                    }
                    addr = addr.replace('주소 ', '').split('지번')[0].trim();
                    
                    const rating = safeText('.star-point') || safeText('span.point') || "0.0";
                    
                    const menuItems = Array.from(document.querySelectorAll('.menu-info li, .menu_info li')).slice(0, 20);
                    const menus = menuItems.map(item => {
                        const m_name = item.querySelector('.nm, .name')?.innerText?.trim() || "";
                        const m_price = item.querySelector('.pr, .price')?.innerText?.trim() || "";
                        return { menu_name: m_name, menu_price: m_price };
                    }).filter(m => m.menu_name);
                    
                    return { addr, rating, menus };
                }
            """)
            
            result["store_address"] = data["addr"]
            result["store_rating"] = self.RATING_PATTERN.search(data["rating"]).group() if self.RATING_PATTERN.search(data["rating"]) else "0.0"
            result["menus_json"] = json.dumps(data["menus"], ensure_ascii=False)
            
            logger.info(f"--- 주소: {result['store_address']}")
            logger.info(f"--- 평점: {result['store_rating']}")
            logger.info(f"--- 메뉴: {len(data['menus'])}건")

            # 성공 판정
            result["status"] = "ok"
            logger.info(f"--- 상세 수집 완료: {store_name}")
            
        except Exception as e:
            result["error_message"] = str(e)
            logger.error(f"!!! 수집 실패 ({store_name}): {str(e)}")
        finally:
            self.stop()
            
        return result

    def batch_extract_details(self, candidates: List[Dict[str, str]], limit: Optional[int] = None):
        """리스트에 있는 여러 매장을 수집하여 저장합니다."""
        results = []
        target_list = candidates[:limit] if limit else candidates
        total = len(target_list)
        
        for idx, item in enumerate(target_list):
            current_idx = idx + 1
            percent = (current_idx / total) * 100
            logger.info(f"[{current_idx}/{total}] ({percent:.1f}%) 처리 중: {item.get('store_name')}")
            
            # 여기서 매번 start/stop을 하면 느리지만, 현재 구조(BaseCrawler.start가 새 페이지 생성)를 유지하거나 리팩토링 가능
            # 일단 안전을 위해 매번 새 브라우저를 띄우는 기존 방식(collect_details.py 방식)을 클래스 메서드로 구현
            res = self.extract_details(item.get("store_url"), item.get("store_name"))
            res.update({"source_region": item.get("source_region", ""), "source_category": item.get("source_category", "")})
            results.append(res)
            
        return results
