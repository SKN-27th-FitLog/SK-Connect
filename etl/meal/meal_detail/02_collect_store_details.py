import argparse
import json
import random
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Set

import pandas as pd
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

PRICE_PATTERN = re.compile(r"([0-9,]+)\s*원")
RATING_PATTERN = re.compile(r"\b([0-5](?:\.\d)?)\b")
REVIEW_COUNT_PATTERN = re.compile(r"(\d+)건\s*의\s*리뷰")

OUTPUT_COLUMNS = [
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
    time.sleep(random.uniform(a, b))


def safe_text(locator, default: str = "") -> str:
    try:
        return locator.inner_text().strip()
    except Exception:
        return default


def parse_price_to_digits(value: Any) -> str:
    if value is None:
        return ""
    match = PRICE_PATTERN.search(str(value))
    return match.group(1).replace(",", "") if match else ""


def expand_menu_section(page, max_clicks: int = 10) -> None:
    labels = ["메뉴 모두보기", "메뉴 모두 보기", "대표메뉴 모두보기", "메뉴 더보기"]
    for _ in range(max_clicks):
        clicked = False
        for label in labels:
            try:
                loc = page.get_by_text(label, exact=False)
                count = min(loc.count(), 5)
            except Exception:
                continue
            for i in range(count):
                btn = loc.nth(i)
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


def extract_store_name(page) -> str:
    for selector in ["h1", "#div_profile h1", ".tit-name", ".PoiHeader h1"]:
        text = safe_text(page.locator(selector).first)
        if text:
            return text.split("\n")[0].strip()
    return ""


def extract_store_address(page) -> str:
    for selector in [".addr", ".address", "text=/지번.*$/"]:
        text = safe_text(page.locator(selector).first)
        if text and len(text) >= 5:
            return text
    body = safe_text(page.locator("body"))
    for line in body.splitlines():
        line = line.strip()
        if "지번" in line and len(line) >= 5:
            return line
    return ""


def extract_store_rating(page) -> str:
    for selector in [".point-num", ".score", ".rate-point"]:
        text = safe_text(page.locator(selector).first)
        match = RATING_PATTERN.search(text)
        if match:
            return match.group(1)
    body = safe_text(page.locator("body"))
    match = RATING_PATTERN.search(body)
    return match.group(1) if match else ""


def extract_review_count(page) -> str:
    body = safe_text(page.locator("body"))
    match = REVIEW_COUNT_PATTERN.search(body)
    return match.group(1) if match else ""


def collect_menus(page, max_items: int = 50) -> List[Dict[str, str]]:
    menus: List[Dict[str, str]] = []
    seen: Set[tuple] = set()
    rows = page.locator("li, tr, [class*='menu'], [id*='menu']")
    try:
        count = min(rows.count(), 300)
    except Exception:
        count = 0

    for i in range(count):
        row = rows.nth(i)
        text = safe_text(row)
        if not text or len(text) > 120:
            continue
        price_match = PRICE_PATTERN.search(text)
        if not price_match:
            continue
        price = price_match.group(1).replace(",", "")
        # 가격 문자열을 제외하고 남은 부분의 줄바꿈과 탭 등 불필요한 공백 제거
        name = text.replace(price_match.group(0), "")
        name = re.sub(r"\s+", " ", name).strip(" -:")
        if not name or len(name) > 100:  # 메뉴 설명이 길 수 있으므로 100자까지 허용
            continue
        key = (name, price)
        if key in seen:
            continue
        menus.append({"menu_name": name, "menu_price": price})
        seen.add(key)
        if len(menus) >= max_items:
            break
    return menus


def load_processed(output_csv: str) -> Set[str]:
    path = Path(output_csv)
    if not path.exists():
        return set()
    try:
        df = pd.read_csv(path)
    except Exception:
        return set()
    if "status" in df.columns:
        df = df[df["status"] == "ok"]
    return set(df.get("store_url", pd.Series(dtype=str)).dropna().astype(str))


def append_row(row: Dict[str, Any], output_csv: str) -> None:
    out = Path(output_csv)
    out.parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame([row])
    for col in OUTPUT_COLUMNS:
        if col not in df.columns:
            df[col] = ""
    df = df[OUTPUT_COLUMNS]
    if out.exists():
        df.to_csv(out, mode="a", header=False, index=False, encoding="utf-8-sig")
    else:
        df.to_csv(out, index=False, encoding="utf-8-sig")


def crawl_one(page, candidate: Dict[str, str]) -> Dict[str, Any]:
    row = {
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
    try:
        response = page.goto(row["store_url"], wait_until="domcontentloaded", timeout=60000)
        if response and response.status >= 400:
            row["status"] = "error"
            row["error_message"] = f"HTTP {response.status}"
            return row
            
        page.wait_for_timeout(2200)
        expand_menu_section(page)
        page.wait_for_timeout(1000)
        body = safe_text(page.locator("body"))
        if "403 Forbidden" in body and len(body) < 500:
            row["status"] = "error"
            row["error_message"] = "403 Forbidden in body"
            return row
            
        menus = collect_menus(page)
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
        row["error_message"] = f"{type(e).__name__}: {e}"
    return row


def main() -> None:
    parser = argparse.ArgumentParser(description="후보 URL에서 맛집 상세 수집")
    BASE_DIR = Path(__file__).resolve().parent.parent
    parser.add_argument("--input", default=str(BASE_DIR / "data" / "shop_candidates.csv"))
    parser.add_argument("--output", default=str(BASE_DIR / "data" / "raw_store_data.csv"))
    parser.add_argument("--headful", action="store_true")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    df = pd.read_csv(args.input)
    if args.limit is not None:
        df = df.head(args.limit).copy()

    # 실패(error)했던 기존 기록들을 CSV에서 미리 제거하여, 아래에 계속 중복 추가되는 것을 방지
    out_path = Path(args.output)
    if out_path.exists():
        try:
            old_df = pd.read_csv(out_path)
            if "status" in old_df.columns:
                old_df = old_df[old_df["status"] == "ok"]
            if "store_name" in old_df.columns:
                old_df = old_df[old_df["store_name"] != "403 Forbidden"]
                
            old_df.to_csv(out_path, index=False, encoding="utf-8-sig")
        except Exception:
            pass

    processed = load_processed(args.output)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not args.headful, slow_mo=300)
        context = browser.new_context(locale="ko-KR", viewport={"width": 1440, "height": 2200})
        page = context.new_page()

        # 구글 광고(Vignette 등)로 인한 스크롤/클릭 방해 차단
        page.route("**/*", lambda route: route.abort() if any(domain in route.request.url for domain in ["googleads", "googlesyndication", "doubleclick"]) else route.continue_())

        total = len(df)
        count = 0
        for _, candidate in df.iterrows():
            count += 1
            store_url = str(candidate.get("store_url", "")).strip()
            if pd.isna(candidate.get("store_url")) or not store_url or store_url.lower() == "nan" or store_url in processed:
                continue
                
            store_name = candidate.get("store_name", "")
            print(f"[{count}/{total}] 맛집 상세 수집 중: {store_name} ...")
            safe_candidate = {k: ("" if pd.isna(v) else str(v)) for k, v in candidate.to_dict().items()}
            row = crawl_one(page, safe_candidate)
            append_row(row, args.output)
            processed.add(store_url)
            print(f"  -> 결과: {row['status']}")
            pause(1.0, 1.8)

        browser.close()


if __name__ == "__main__":
    main()
