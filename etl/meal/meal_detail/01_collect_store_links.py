import argparse
import csv
import random
import time
from pathlib import Path
from typing import Dict, List, Set
from urllib.parse import urljoin

import pandas as pd
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

BASE_URL = "https://www.diningcode.com"
# 실제 목록 URL 규칙은 사이트 구조에 맞게 수정 필요
LISTING_URL_TEMPLATE = (
    "https://www.diningcode.com/list.dc?query={region}%20{category}"
)

OUTPUT_COLUMNS = [
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
    time.sleep(random.uniform(a, b))


def safe_text(locator, default: str = "") -> str:
    try:
        return locator.inner_text().strip()
    except Exception:
        return default


def safe_attr(locator, name: str, default: str = "") -> str:
    try:
        value = locator.get_attribute(name)
        return value.strip() if value else default
    except Exception:
        return default


def append_rows(rows: List[Dict], output_csv: str) -> None:
    if not rows:
        return
    output_path = Path(output_csv)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(rows)
    for col in OUTPUT_COLUMNS:
        if col not in df.columns:
            df[col] = ""
    df = df[OUTPUT_COLUMNS]
    if output_path.exists():
        df.to_csv(output_path, mode="a", header=False, index=False, encoding="utf-8-sig")
    else:
        df.to_csv(output_path, index=False, encoding="utf-8-sig")


def load_seen_urls(output_csv: str) -> Set[str]:
    path = Path(output_csv)
    if not path.exists():
        return set()
    try:
        df = pd.read_csv(path)
    except Exception:
        return set()
    return set(df.get("store_url", pd.Series(dtype=str)).dropna().astype(str).str.strip())


def scroll_listing_page(page, rounds: int = 5) -> None:
    for _ in range(rounds):
        try:
            page.mouse.wheel(0, 2200)
            pause(0.5, 0.9)
        except Exception:
            break


def collect_cards_on_page(page) -> List[Dict[str, str]]:
    candidates: List[Dict[str, str]] = []
    seen: Set[str] = set()

    selectors = [
        "a[href*='profile.php?rid=']",
        "a[href*='/profile.php?rid=']",
    ]

    for selector in selectors:
        anchors = page.locator(selector)
        try:
            count = min(anchors.count(), 100)
        except Exception:
            count = 0

        for idx in range(count):
            anchor = anchors.nth(idx)
            href = safe_attr(anchor, "href")
            text = safe_text(anchor)
            if not href:
                continue
            full_url = urljoin(BASE_URL, href)
            if full_url in seen:
                continue
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            store_name = lines[0] if lines else ""
            store_summary = " | ".join(lines[1:4]) if len(lines) > 1 else ""
            candidates.append(
                {
                    "store_name": store_name,
                    "store_url": full_url,
                    "store_summary": store_summary,
                }
            )
            seen.add(full_url)
    return candidates


def collect_store_links(page, region: str, category: str, max_pages: int) -> List[Dict]:
    rows: List[Dict] = []

    for page_no in range(1, max_pages + 1):
        listing_url = LISTING_URL_TEMPLATE.format(region=region, category=category)
        # 사이트에 page 파라미터가 있으면 여기에 연결
        if page_no > 1:
            listing_url = f"{listing_url}&page={page_no}"

        try:
            page.goto(listing_url, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(1800)
            scroll_listing_page(page, rounds=4)
            cards = collect_cards_on_page(page)
            if not cards:
                rows.append(
                    {
                        "source_region": region,
                        "source_category": category,
                        "page_no": page_no,
                        "store_name": "",
                        "store_url": "",
                        "store_summary": "",
                        "collected_at": pd.Timestamp.now().isoformat(),
                        "status": "empty",
                        "error_message": "no_cards_found",
                    }
                )
                break

            for card in cards:
                rows.append(
                    {
                        "source_region": region,
                        "source_category": category,
                        "page_no": page_no,
                        "store_name": card["store_name"],
                        "store_url": card["store_url"],
                        "store_summary": card["store_summary"],
                        "collected_at": pd.Timestamp.now().isoformat(),
                        "status": "ok",
                        "error_message": "",
                    }
                )
        except PlaywrightTimeoutError:
            rows.append(
                {
                    "source_region": region,
                    "source_category": category,
                    "page_no": page_no,
                    "store_name": "",
                    "store_url": "",
                    "store_summary": "",
                    "collected_at": pd.Timestamp.now().isoformat(),
                    "status": "error",
                    "error_message": "timeout",
                }
            )
        except Exception as e:
            rows.append(
                {
                    "source_region": region,
                    "source_category": category,
                    "page_no": page_no,
                    "store_name": "",
                    "store_url": "",
                    "store_summary": "",
                    "collected_at": pd.Timestamp.now().isoformat(),
                    "status": "error",
                    "error_message": f"{type(e).__name__}: {e}",
                }
            )
        pause(1.0, 1.8)

    return rows


def read_targets(path: str) -> List[Dict[str, str]]:
    with open(path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = []
        for row in reader:
            rows.append(
                {
                    "region": str(row.get("region", "")).strip(),
                    "category": str(row.get("category", "")).strip(),
                }
            )
    return [r for r in rows if r["region"] and r["category"]]


def main() -> None:
    parser = argparse.ArgumentParser(description="맛집 목록 페이지에서 후보 URL 수집")
    parser.add_argument("--targets", required=True, help="region/category CSV")
    parser.add_argument("--output", default="../data/shop_candidates.csv", help="후보 URL CSV")
    parser.add_argument("--max-pages", type=int, default=3, help="지역/카테고리별 최대 페이지")
    parser.add_argument("--headful", action="store_true")
    args = parser.parse_args()

    targets = read_targets(args.targets)
    seen_urls = load_seen_urls(args.output)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not args.headful, slow_mo=300)
        context = browser.new_context(locale="ko-KR", viewport={"width": 1440, "height": 2200})
        page = context.new_page()

        for target in targets:
            region = target["region"]
            category = target["category"]
            rows = collect_store_links(page, region, category, args.max_pages)
            deduped: List[Dict] = []
            for row in rows:
                url = row.get("store_url", "")
                if url and url in seen_urls:
                    continue
                if url:
                    seen_urls.add(url)
                deduped.append(row)
            append_rows(deduped, args.output)

        browser.close()


if __name__ == "__main__":
    main()
