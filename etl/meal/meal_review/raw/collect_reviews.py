import argparse
import json
import random
import re
import time
import urllib.request
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Final, Set
from urllib.error import HTTPError

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

# 패턴 및 상수 정의
RATING_PATTERN: Final[re.Pattern] = re.compile(r"[0-5](?:\.\d)?")
DATE_PATTERN: Final[re.Pattern] = re.compile(r"\d{4}[.-]\d{1,2}[.-]\d{1,2}")
SAFE_FILENAME_PATTERN: Final[re.Pattern] = re.compile(r"[^0-9a-zA-Z가-힣._-]+")

def pause(a: float = 0.8, b: float = 1.4) -> None:
    time.sleep(random.uniform(a, b))

def normalize_space(value: str) -> str:
    return re.sub(r"\s+", " ", str(value)).strip()

def safe_text(locator: Locator, default: str = "") -> str:
    try:
        return locator.inner_text().strip()
    except Exception:
        return default

def slugify_filename(text: str, max_len: int = 80) -> str:
    text = normalize_space(text)
    text = SAFE_FILENAME_PATTERN.sub("_", text)
    text = text.strip("._-")
    return text[:max_len] if text else "unknown"

def scroll_reviews(page: Page, rounds: int = 5) -> None:
    for i in range(rounds):
        try:
            page.mouse.wheel(0, 3000)
            pause(0.6, 1.0)
        except Exception:
            break

def collect_reviews_structured(page: Page, store_name: str, max_items: int = 500) -> List[Dict[str, object]]:
    reviews: List[Dict[str, object]] = []
    seen: Set[tuple] = set()
    blocks: Locator = page.locator("div[id^='div_review_']")
    count: int = min(blocks.count(), max_items)

    for i in range(count):
        try:
            block: Locator = blocks.nth(i)
            review_id: str = block.get_attribute("id") or ""
            
            # 평점/날짜/본문 기수집 로직 (Any 배제)
            rating_text: str = safe_text(block.locator(".total_score").first)
            rating_match = RATING_PATTERN.search(rating_text)
            rating = rating_match.group(0) if rating_match else ""

            date_text: str = safe_text(block.locator("span.date").first)
            date_match = DATE_PATTERN.search(date_text)
            date = date_match.group(0) if date_match else ""

            content: str = normalize_space(safe_text(block.locator("div.review_contents.btxt").first))
            if not content: continue

            # 중복 체크
            key: tuple = (content[:200], date, rating)
            if key in seen: continue
            seen.add(key)

            reviews.append({
                "review_id": review_id,
                "rating": rating,
                "date": date,
                "content": content
            })
        except Exception:
            continue
    return reviews

def main() -> None:
    parser = argparse.ArgumentParser(description="맛집 리뷰 데이터 수집 (Raw)")
    parser.add_argument("--input", required=True, help="기수집된 식당 정보 CSV")
    parser.add_argument("--headful", action="store_true")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    df_stores: pd.DataFrame = pd.read_csv(args.input)
    if args.limit:
        df_stores = df_stores.head(args.limit)

    with sync_playwright() as p:
        browser: Browser = p.chromium.launch(headless=not args.headful, slow_mo=300)
        context: BrowserContext = browser.new_context(locale="ko-KR")
        page: Page = context.new_page()

        all_review_results: List[Dict[str, object]] = []

        for _, row in df_stores.iterrows():
            url: str = str(row["store_url"])
            name: str = str(row["store_name"])
            logger.info(f"🚀 리뷰 수집 중: {name}")
            
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=60000)
                page.wait_for_timeout(2000)
                scroll_reviews(page)
                
                reviews: List[Dict[str, object]] = collect_reviews_structured(page, name)
                for rv in reviews:
                    rv.update({"store_name": name, "store_url": url})
                    all_review_results.append(rv)
            except Exception as e:
                logger.error(f"❌ 리뷰 수집 실패 ({name}): {str(e)}")

        browser.close()

    if all_review_results:
        df_rv: pd.DataFrame = pd.DataFrame(all_review_results)
        save_path: Path = get_hive_path("process=raw", "service=review", "success")
        df_rv.to_csv(save_path, index=False, encoding="utf-8-sig")
        logger.info(f"✅ 리뷰 {len(df_rv)}건 수집 완료 (Hive: {save_path.name})")

if __name__ == "__main__":
    main()
