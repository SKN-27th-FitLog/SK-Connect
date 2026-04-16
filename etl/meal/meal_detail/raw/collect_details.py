import argparse
import json
import random
import re
import time
import sys
from pathlib import Path
from typing import Any, Dict, List, Set, Final, Optional

import pandas as pd
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright, Page, Locator, Browser, BrowserContext

# 상위 디렉토리의 유틸리티 임포트
CURRENT_DIR: Final[Path] = Path(__file__).resolve().parent
PROJECT_ROOT: Final[Path] = CURRENT_DIR.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from common_utils import (
    logger,
    get_hive_path,
    get_project_root
)

# 정규표현식 패턴 정의
PRICE_PATTERN: Final[re.Pattern] = re.compile(r"([0-9,]+)\s*원")      # 가격 추출
RATING_PATTERN: Final[re.Pattern] = re.compile(r"\b([0-5](?:\.\d)?)\b") # 평점 추출
REVIEW_COUNT_PATTERN: Final[re.Pattern] = re.compile(r"(\d+)건\s*의\s*리뷰") # 리뷰 개수 추출

# 수집 결과 데이터 컬럼 정의
OUTPUT_COLUMNS: Final[List[str]] = [
    "source_region",
    "source_category",
    "store_name",
    "store_url",
    "store_address",
    "store_rating",
    "review_count",
    "menus_json",
    "raw_body_excerpt",
    "status",
    "error_message",
]

def pause(a: float = 0.7, b: float = 1.4) -> None:
    """무작위 일시정지"""
    time.sleep(random.uniform(a, b))

def safe_text(locator: Locator, default: str = "") -> str:
    """텍스트를 안전하게 추출합니다."""
    try:
        return locator.inner_text().strip()
    except Exception:
        return default

def parse_price_to_digits(value: Optional[str]) -> str:
    """가격 문자열에서 숫자만 추출합니다."""
    if not value:
        return ""
    match: Optional[re.Match] = PRICE_PATTERN.search(value)
    return match.group(1).replace(",", "") if match else ""

def expand_menu_section(page: Page, max_clicks: int = 10) -> None:
    """메뉴 상세 보기 버튼이 있을 경우 클릭하여 노출시킵니다."""
    labels: List[str] = ["메뉴 모두보기", "메뉴 모두 보기", "대표메뉴 모두보기", "메뉴 더보기"]
    for _ in range(max_clicks):
        clicked: bool = False
        for label in labels:
            try:
                loc: Locator = page.get_by_text(label, exact=False)
                count: int = min(loc.count(), 5)
            except Exception:
                continue
            for i in range(count):
                btn: Locator = loc.nth(i)
                try:
                    if not btn.is_visible(timeout=700):
                        continue
                    btn.scroll_into_view_if_needed(timeout=2000)
                    page.wait_for_timeout(200)
                    btn.click(timeout=2000)
                    clicked = True
                    pause(0.5, 0.9)
                    break
                except Exception:
                    continue
            if clicked:
                break
        if not clicked:
            break

def extract_store_name(page: Page) -> str:
    """가게 이름을 추출합니다."""
    for selector in ["h1", "#div_profile h1", ".tit-name", ".PoiHeader h1"]:
        text: str = safe_text(page.locator(selector).first)
        if text:
            return text.split("\n")[0].strip()
    return ""

def extract_store_address(page: Page) -> str:
    """가게 주소를 추출합니다."""
    for selector in [".addr", ".address", "text=/지번.*$/"]:
        text: str = safe_text(page.locator(selector).first)
        if text and len(text) >= 5:
            return text
    body: str = safe_text(page.locator("body"))
    for line in body.splitlines():
        line = line.strip()
        if "지번" in line and len(line) >= 5:
            return line
    return ""

def extract_store_rating(page: Page) -> str:
    """평점을 추출합니다."""
    for selector in [".point-num", ".score", ".rate-point"]:
        text: str = safe_text(page.locator(selector).first)
        match: Optional[re.Match] = RATING_PATTERN.search(text)
        if match:
            return str(match.group(1))
    body: str = safe_text(page.locator("body"))
    match_body: Optional[re.Match] = RATING_PATTERN.search(body)
    return str(match_body.group(1)) if match_body else ""

def extract_review_count(page: Page) -> str:
    """리뷰 개수를 추출합니다."""
    body: str = safe_text(page.locator("body"))
    match: Optional[re.Match] = REVIEW_COUNT_PATTERN.search(body)
    return str(match.group(1)) if match else ""

def collect_menus(page: Page, max_items: int = 50) -> List[Dict[str, str]]:
    """메뉴 정보를 수집합니다."""
    menus: List[Dict[str, str]] = []
    seen: Set[tuple[str, str]] = set()
    rows: Locator = page.locator("li, tr, [class*='menu'], [id*='menu']")
    try:
        count: int = min(rows.count(), 300)
    except Exception:
        count = 0

    for i in range(count):
        row: Locator = rows.nth(i)
        text: str = safe_text(row)
        if not text or len(text) > 120:
            continue
        price_match: Optional[re.Match] = PRICE_PATTERN.search(text)
        if not price_match:
            continue
        price: str = price_match.group(1).replace(",", "")
        name: str = text.replace(price_match.group(0), "")
        name = re.sub(r"\s+", " ", name).strip(" -:")
        if not name or len(name) > 100:
            continue
        key: tuple[str, str] = (name, price)
        if key in seen:
            continue
        menus.append({"menu_name": name, "menu_price": price})
        seen.add(key)
        if len(menus) >= max_items:
            break
    return menus

def crawl_one(page: Page, candidate: Dict[str, str]) -> Dict[str, str]:
    """단일 식당 정보를 수집합니다."""
    row: Dict[str, str] = {
        "source_region": candidate.get("source_region", ""),
        "source_category": candidate.get("source_category", ""),
        "store_name": candidate.get("store_name", ""),
        "store_url": candidate.get("store_url", ""),
        "store_address": "",
        "store_rating": "",
        "review_count": "",
        "menus_json": "[]",
        "raw_body_excerpt": "",
        "status": "ok",
        "error_message": "",
    }
    url: str = row["store_url"]
    if not url:
        row["status"] = "error"
        row["error_message"] = "empty_url"
        return row

    try:
        response = page.goto(url, wait_until="domcontentloaded", timeout=60000)
        if response and response.status >= 400:
            row["status"] = "error"
            row["error_message"] = f"HTTP {response.status}"
            return row
            
        page.wait_for_timeout(2200)
        expand_menu_section(page)
        page.wait_for_timeout(1000)
        
        body: str = safe_text(page.locator("body"))
        if "403 Forbidden" in body and len(body) < 500:
            row["status"] = "error"
            row["error_message"] = "403_forbidden"
            return row
            
        menus: List[Dict[str, str]] = collect_menus(page)
        row.update(
            {
                "store_name": extract_store_name(page) or row["store_name"],
                "store_address": extract_store_address(page),
                "store_rating": extract_store_rating(page),
                "review_count": extract_review_count(page),
                "menus_json": json.dumps(menus, ensure_ascii=False),
                "raw_body_excerpt": body[:1000],
            }
        )
    except PlaywrightTimeoutError:
        row["status"] = "error"
        row["error_message"] = "timeout"
    except Exception as e:
        row["status"] = "error"
        row["error_message"] = f"{type(e).__name__}: {str(e)}"
    return row

def load_candidates(input_csv: str) -> List[Dict[str, str]]:
    """후보 URL 목록을 로드합니다."""
    path: Path = Path(input_csv)
    if not path.exists():
        logger.error(f"입력 파일 없음: {input_csv}")
        return []
    df: pd.DataFrame = pd.read_csv(path)
    # NaN 방지 및 문자열 변환
    return [{str(k): str(v) for k, v in r.items() if pd.notna(v)} for r in df.to_dict("records")]

def main() -> None:
    parser = argparse.ArgumentParser(description="맛집 상세 정보 수집")
    PROJECT_ROOT: Path = get_project_root()
    
    # 01 단계의 결과인 raw Hive 경로(혹은 로컬 수집 결과)를 기반으로 입력을 받아야 함
    # 여기서는 유연하게 인자로 받음
    parser.add_argument("--input", required=True, help="수집된 링크 정보 CSV")
    parser.add_argument("--headful", action="store_true")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    candidates: List[Dict[str, str]] = load_candidates(args.input)
    if args.limit:
        candidates = candidates[:args.limit]

    results: List[Dict[str, str]] = []
    
    with sync_playwright() as p:
        user_agent: str = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
        )
        browser: Browser = p.chromium.launch(headless=not args.headful, slow_mo=300)
        context: BrowserContext = browser.new_context(
            user_agent=user_agent,
            locale="ko-KR", 
            viewport={"width": 1440, "height": 2200}
        )
        page: Page = context.new_page()
        page.route("**/*", lambda route: route.abort() if any(domain in route.request.url for domain in ["googleads", "googlesyndication", "doubleclick"]) else route.continue_())

        total: int = len(candidates)
        for idx, candidate in enumerate(candidates):
            logger.info(f"[{idx+1}/{total}] 상세 정보 수집 중: {candidate.get('store_name')}")
            row: Dict[str, str] = crawl_one(page, candidate)
            results.append(row)
            pause(1.0, 1.8)

        browser.close()

    if results:
        df: pd.DataFrame = pd.DataFrame(results)
        # [수정] 가게 상세 정보 수집 결과를 Hive 스타일 데이터 레이크(raw/shop)에 저장합니다.
        # AWS 환경과의 호환성을 위해 계층 구조를 그대로 사용합니다.
        save_path: Path = get_hive_path("process=raw", "service=shop", "success")
        df.to_csv(save_path, index=False, encoding="utf-8-sig")
        logger.info(f"✅ 상세 수집 완료. Hive 저장(raw/shop): {save_path.name}")

if __name__ == "__main__":
    main()
