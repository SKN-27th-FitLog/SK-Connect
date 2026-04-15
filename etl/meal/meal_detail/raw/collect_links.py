import argparse
import csv
import random
import time
import sys
from pathlib import Path
from typing import Dict, List, Set, Final, Optional
from urllib.parse import urljoin

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

# 다이닝코드 기본 URL 및 검색 템플릿 설정
BASE_URL: Final[str] = "https://www.diningcode.com"
LISTING_URL_TEMPLATE: Final[str] = (
    "https://www.diningcode.com/list.dc?query={region}%20{category}"
)

# 수집 데이터 결과 컬럼 정의
OUTPUT_COLUMNS: Final[List[str]] = [
    "source_region",
    "source_category",
    "page_no",
    "store_name",
    "store_url",
    "store_summary",
    "collected_at",
    "status",
    "error_message",
]

def pause(a: float = 0.7, b: float = 1.4) -> None:
    """사람처럼 보이게 하기 위한 무작위 일시정지"""
    time.sleep(random.uniform(a, b))

def safe_text(locator: Locator, default: str = "") -> str:
    """Playwright locator로부터 안전하게 텍스트를 추출합니다."""
    try:
        return locator.inner_text().strip()
    except Exception:
        return default

def safe_attr(locator: Locator, name: str, default: str = "") -> str:
    """Playwright locator로부터 안전하게 속성값을 추출합니다."""
    try:
        value: Optional[str] = locator.get_attribute(name)
        return value.strip() if value else default
    except Exception:
        return default

def save_to_hive(rows: List[Dict[str, str]], region: str, category: str) -> None:
    """
    수집된 맛집 링크 데이터 후보들을 Hive 스타일 데이터 레이크(process=raw, service=shop)에 저장합니다.
    AWS S3 호환을 위해 계층적 폴더 구조(year/month/day/status)를 강제로 유지합니다.
    """
    # [수정] 결과가 없더라도 헤더를 포함한 파일을 생성하여 다음 단계의 '파일 없음' 오류를 방지합니다.
    df: pd.DataFrame = pd.DataFrame(rows)
    for col in OUTPUT_COLUMNS:
        if col not in df.columns:
            df[col] = ""
    df = df[OUTPUT_COLUMNS]
    
    save_path: Path = get_hive_path("process=raw", "service=shop", "success")
    df.to_csv(save_path, index=False, encoding="utf-8-sig")
    
    if rows:
        logger.info(f"📂 데이터 레이크(raw/shop) 저장 완료: {save_path.name}")
    else:
        logger.warning(f"💡 수집된 결과가 없지만 빈 파일을 생성했습니다: {save_path.name}")

def load_seen_urls(input_csv: Optional[str]) -> Set[str]:
    """이전 수집 결과에서 URL 목록을 로드하여 중복 수집을 방지합니다."""
    if not input_csv:
        return set()
    path: Path = Path(input_csv)
    if not path.exists():
        return set()
    try:
        df: pd.DataFrame = pd.read_csv(path)
        return set(df.get("store_url", pd.Series(dtype=str)).dropna().astype(str).str.strip())
    except Exception as e:
        logger.error(f"기수집 URL 로드 실패: {str(e)}")
        return set()

def scroll_listing_page(page: Page, rounds: int = 5) -> None:
    """목록 페이지를 아래로 스크롤하여 동적 로딩된 카드를 노출시킵니다."""
    for _ in range(rounds):
        try:
            page.mouse.wheel(0, 2200)
            pause(0.5, 0.9)
        except Exception:
            break

def collect_cards_on_page(page: Page) -> List[Dict[str, str]]:
    """현재 페이지에서 맛집 카드 정보를 추출합니다."""
    candidates: List[Dict[str, str]] = []
    seen: Set[str] = set()

    selectors: List[str] = [
        "a[href*='profile.php?rid=']",
        "a[href*='/profile.php?rid=']",
    ]

    for selector in selectors:
        anchors: Locator = page.locator(selector)
        try:
            count: int = min(anchors.count(), 100)
        except Exception:
            count = 0

        for idx in range(count):
            anchor: Locator = anchors.nth(idx)
            href: str = safe_attr(anchor, "href")
            text: str = safe_text(anchor)
            if not href:
                continue
            full_url: str = urljoin(BASE_URL, href)
            if full_url in seen:
                continue
            lines: List[str] = [line.strip() for line in text.splitlines() if line.strip()]
            store_name: str = lines[0] if lines else ""
            store_summary: str = " | ".join(lines[1:4]) if len(lines) > 1 else ""
            candidates.append(
                {
                    "store_name": store_name,
                    "store_url": full_url,
                    "store_summary": store_summary,
                }
            )
            seen.add(full_url)
    return candidates

def collect_store_links(page: Page, region: str, category: str, max_pages: int) -> List[Dict[str, str]]:
    """특정 지역 및 카테고리에 대해 여러 페이지를 돌며 맛집 링크를 수집합니다."""
    rows: List[Dict[str, str]] = []

    for page_no in range(1, max_pages + 1):
        listing_url: str = LISTING_URL_TEMPLATE.format(region=region, category=category)
        if page_no > 1:
            listing_url = f"{listing_url}&page={page_no}"

        logger.info(f"  -> {page_no}페이지 탐색 중...")
        try:
            page.goto(listing_url, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(1800)
            scroll_listing_page(page, rounds=4)
            cards: List[Dict[str, str]] = collect_cards_on_page(page)
            if not cards:
                logger.warning(f"     (결과 없음: {region} {category})")
                break

            for card in cards:
                rows.append(
                    {
                        "source_region": region,
                        "source_category": category,
                        "page_no": str(page_no),
                        "store_name": card["store_name"],
                        "store_url": card["store_url"],
                        "store_summary": card["store_summary"],
                        "collected_at": pd.Timestamp.now().isoformat(),
                        "status": "ok",
                        "error_message": "",
                    }
                )
        except PlaywrightTimeoutError:
            logger.error(f"타임아웃 발생: {listing_url}")
            rows.append(
                {
                    "source_region": region,
                    "source_category": category,
                    "page_no": str(page_no),
                    "store_name": "",
                    "store_url": "",
                    "store_summary": "",
                    "collected_at": pd.Timestamp.now().isoformat(),
                    "status": "error",
                    "error_message": "timeout",
                }
            )
        except Exception as e:
            logger.error(f"수집 중 알 수 없는 오류: {str(e)}")
            rows.append(
                {
                    "source_region": region,
                    "source_category": category,
                    "page_no": str(page_no),
                    "store_name": "",
                    "store_url": "",
                    "store_summary": "",
                    "collected_at": pd.Timestamp.now().isoformat(),
                    "status": "error",
                    "error_message": f"{type(e).__name__}: {str(e)}",
                }
            )
        pause(1.0, 1.8)

    return rows

def read_targets(path: str) -> List[Dict[str, str]]:
    """수집 대상(지역/카테고리) CSV 파일을 로드합니다."""
    targets: List[Dict[str, str]] = []
    with open(path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            region: str = str(row.get("region", "")).strip()
            category: str = str(row.get("category", "")).strip()
            if region and category:
                targets.append({"region": region, "category": category})
    return targets

def main() -> None:
    parser = argparse.ArgumentParser(description="다이닝코드 맛집 목록 페이지에서 후보 URL 수집")
    parser.add_argument("--targets", required=True, help="지역/카테고리가 담긴 CSV 파일 경로")
    parser.add_argument("--max-pages", type=int, default=3, help="지역/카테고리별 최대 수집 페이지 수")
    parser.add_argument("--headful", action="store_true", help="브라우저 창을 보이게 실행 여부")
    args = parser.parse_args()

    targets: List[Dict[str, str]] = read_targets(args.targets)
    
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

        for target in targets:
            region: str = target["region"]
            category: str = target["category"]
            logger.info(f"[{region} {category}] 맛집 목록 수집 시작... (최대 {args.max_pages} 페이지)")
            
            rows: List[Dict[str, str]] = collect_store_links(page, region, category, args.max_pages)
            save_to_hive(rows, region, category)

        browser.close()

if __name__ == "__main__":
    main()
