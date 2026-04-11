import argparse
import json
import random
import re
import time
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.error import HTTPError

import pandas as pd
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

RATING_PATTERN = re.compile(r"[0-5](?:\.\d)?")
DATE_PATTERN = re.compile(r"\d{4}[.-]\d{1,2}[.-]\d{1,2}")
SAFE_FILENAME_PATTERN = re.compile(r"[^0-9a-zA-Z가-힣._-]+")

SUMMARY_COLUMNS = [
    "store_name",
    "store_url",
    "status",
    "skip_reason",
    "review_count",
    "json_path",
]

def pause(a: float = 0.8, b: float = 1.4) -> None:
    time.sleep(random.uniform(a, b))

def normalize_space(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()

def safe_text(locator, default: str = "") -> str:
    try:
        return locator.inner_text().strip()
    except Exception:
        return default

def safe_count(locator, default: int = 0) -> int:
    try:
        return locator.count()
    except Exception:
        return default

def slugify_filename(text: str, max_len: int = 80) -> str:
    text = normalize_space(text)
    text = SAFE_FILENAME_PATTERN.sub("_", text)
    text = text.strip("._-")
    if not text:
        text = "unknown"
    return text[:max_len]

def append_summary_csv(data: Dict[str, Any], output_csv: str) -> None:
    row = {col: data.get(col, "") for col in SUMMARY_COLUMNS}
    row_df = pd.DataFrame([row])
    output_path = Path(output_csv)

    if not output_path.exists():
        row_df.to_csv(output_path, index=False, encoding="utf-8-sig")
    else:
        row_df.to_csv(output_path, mode="a", header=False, index=False, encoding="utf-8-sig")

def get_processed_urls(output_csv: str) -> set:
    output_path = Path(output_csv)
    if not output_path.exists():
        return set()
    try:
        df = pd.read_csv(output_path)
    except Exception:
        return set()
    return set(df.get("store_url", pd.Series(dtype=str)).dropna().astype(str).str.strip())

def is_page_not_found(page) -> bool:
    body_text = safe_text(page.locator("body"))
    bad_markers = [
        "페이지를 찾을 수 없습니다",
        "존재하지 않는",
        "잘못된 접근",
        "요청하신 페이지를 찾을 수 없습니다",
    ]
    return any(marker in body_text for marker in bad_markers)

def expand_review_section(page, max_clicks: int = 80) -> int:
    clicked_count = 0
    button_texts = [
        "평가 더보기",
        "리뷰 더보기",
        "방문자 리뷰 더보기",
        "더보기",
    ]

    for _ in range(max_clicks):
        clicked = False
        for label in button_texts:
            try:
                locator = page.get_by_text(label, exact=False)
                count = min(safe_count(locator), 10)
            except Exception:
                continue

            for idx in range(count):
                btn = locator.nth(idx)
                try:
                    if not btn.is_visible(timeout=700):
                        continue
                    btn.scroll_into_view_if_needed(timeout=2000)
                    page.wait_for_timeout(250)
                    try:
                        btn.click(timeout=2500)
                    except Exception:
                        btn.click(force=True, timeout=2500)

                    clicked_count += 1
                    clicked = True
                    print(f"   ↳ 리뷰 버튼 클릭: {label} ({clicked_count})")
                    pause(0.7, 1.1)
                    break
                except Exception:
                    continue
            if clicked:
                break
        if not clicked:
            try:
                page.mouse.wheel(0, 2600)
                pause(0.4, 0.8)
            except Exception:
                pass
            visible_found = False
            for label in button_texts:
                try:
                    locator = page.get_by_text(label, exact=False)
                    count = min(safe_count(locator), 5)
                    for idx in range(count):
                        try:
                            if locator.nth(idx).is_visible(timeout=400):
                                visible_found = True
                                break
                        except Exception:
                            continue
                    if visible_found:
                        break
                except Exception:
                    continue
            if not visible_found:
                break
    return clicked_count

def scroll_reviews(page, rounds: int = 5) -> None:
    for i in range(rounds):
        try:
            page.mouse.wheel(0, 3000)
            print(f"   ↳ 추가 스크롤 {i + 1}/{rounds}")
            pause(0.6, 1.0)
        except Exception:
            break

def parse_keywords(raw_text: str) -> List[str]:
    text = normalize_space(raw_text)
    if not text:
        return []
    parts = re.split(r"[,/]|(?:\s{2,})|\n", text)
    keywords = []
    for part in parts:
        kw = normalize_space(part)
        if not kw:
            continue
        if kw not in keywords:
            keywords.append(kw)
    return keywords

def download_review_images(img_srcs: List[str], store_name: str, review_identifier: str, img_dir: str) -> List[str]:
    local_paths = []
    safe_store_name = slugify_filename(store_name)
    save_folder = Path(img_dir) / safe_store_name
    save_folder.mkdir(parents=True, exist_ok=True)
    
    # Custom opener to avoid 403 Forbidden
    opener = urllib.request.build_opener()
    opener.addheaders = [('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)')]
    urllib.request.install_opener(opener)

    for idx, src in enumerate(img_srcs):
        try:
            # Construct absolute URL
            if src.startswith("//"):
                src = "https:" + src
            elif src.startswith("/"):
                src = "https://www.diningcode.com" + src
                
            ext = src.split(".")[-1][:4] if "." in src[-6:] else "jpg"
            img_name = f"{review_identifier}_{idx}.{ext}" if review_identifier else f"review_img_{int(time.time())}_{idx}.{ext}"
            
            # removing query params from extension if any
            img_name = img_name.split("?")[0]
            
            save_path = save_folder / img_name
            urllib.request.urlretrieve(src, str(save_path))
            
            # Store unix-style relative path inside json
            unix_path = f"{safe_store_name}/{img_name}"
            local_paths.append(unix_path)
            time.sleep(0.1)
        except Exception as e:
            # 썸네일이나 비공개 이미지 다운로드 실패 표기 무시
            pass
            
    return local_paths

def collect_reviews_structured(page, store_name: str, img_dir: str, max_items: int = 500) -> List[Dict[str, Any]]:
    reviews: List[Dict[str, Any]] = []
    seen = set()

    blocks = page.locator("div[id^='div_review_']")
    count = min(safe_count(blocks), max_items)
    print(f"   ↳ 리뷰 블록 수: {count}")

    for i in range(count):
        try:
            block = blocks.nth(i)
            review_id = ""
            try:
                review_id = block.get_attribute("id") or ""
            except Exception:
                pass

            rating = ""
            try:
                rating_text = safe_text(block.locator(".total_score").first)
                match = RATING_PATTERN.search(rating_text)
                if match:
                    rating = match.group(0)
            except Exception:
                pass

            date = ""
            try:
                date_text = safe_text(block.locator("span.date").first)
                date_match = DATE_PATTERN.search(date_text)
                date = date_match.group(0) if date_match else normalize_space(date_text)
            except Exception:
                pass

            content = ""
            try:
                content = safe_text(block.locator("div.review_contents.btxt").first)
                content = normalize_space(content)
            except Exception:
                pass

            if not content:
                continue

            keywords: List[str] = []
            try:
                kw_text = safe_text(block.locator("p.new-keyword_list").first)
                keywords = parse_keywords(kw_text)
            except Exception:
                keywords = []
                
            # 이미지 파싱 및 다운로드
            img_srcs = []
            try:
                imgs = block.locator("img")
                count_imgs = safe_count(imgs)
                for img_idx in range(count_imgs):
                    src = imgs.nth(img_idx).get_attribute("src") or imgs.nth(img_idx).get_attribute("data-src")
                    # 다이닝코드 프로필 사진 제외 (화면에 노출된 리뷰 첨부사진만 추출)
                    if src and ("profile" not in src and "icon" not in src):
                        img_srcs.append(src)
            except Exception:
                pass
                
            local_image_paths = []
            if img_srcs:
                safe_rv_id = review_id if review_id else f"rv_{i}"
                local_image_paths = download_review_images(img_srcs, store_name, safe_rv_id, img_dir)

            key = (content[:250], date, rating)
            if key in seen:
                continue

            reviews.append(
                {
                    "review_id": review_id,
                    "rating": rating,
                    "date": date,
                    "content": content,
                    "keywords": keywords,
                    "image_paths": local_image_paths,
                }
            )
            seen.add(key)
        except Exception:
            continue
    return reviews


def crawl_one_store_reviews(
    page,
    store_url: str,
    store_name: str,
    img_dir: str,
    max_expand_clicks: int = 80,
    max_review_items: int = 500,
    extra_scroll_rounds: int = 5,
) -> Dict[str, Any]:
    print("\n==============================")
    print(f"🚀 리뷰 파싱 시작: {store_name}")
    print(f"🔗 URL: {store_url}")
    print("==============================")

    result: Dict[str, Any] = {
        "store_name": store_name,
        "store_url": store_url,
        "status": "error",
        "skip_reason": "",
        "review_count": 0,
        "reviews": [],
    }

    try:
        page.goto(store_url, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(2500)
    except PlaywrightTimeoutError:
        print("❌ detail_timeout")
        result["skip_reason"] = "detail_timeout"
        return result
    except Exception as e:
        print(f"❌ detail_page_error: {e}")
        result["skip_reason"] = "detail_page_error"
        return result

    pause(1.0, 1.8)

    if is_page_not_found(page):
        print("❌ 페이지 없음 → 스킵")
        result["skip_reason"] = "page_not_found"
        return result

    print("🧾 리뷰 더보기 확장 중...")
    clicks = expand_review_section(page, max_clicks=max_expand_clicks)
    print(f"   ↳ 총 클릭 수: {clicks}")

    print("📜 추가 스크롤 진행 중...")
    scroll_reviews(page, rounds=extra_scroll_rounds)

    page.wait_for_timeout(1500)

    print("📊 리뷰 데이터 추출 및 이미지 다운로드 중...")
    reviews = collect_reviews_structured(page, store_name, img_dir, max_items=max_review_items)

    result["reviews"] = reviews
    result["review_count"] = len(reviews)
    result["status"] = "ok"

    print(f"✅ 리뷰 수집 완료: {len(reviews)}개 (이미지 폴더: {img_dir})")
    return result

def save_store_reviews_json(data: Dict[str, Any], output_dir: str, seq_no: int) -> str:
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    
    store_name = data.get("store_name", f"store_{seq_no}")
    safe_name = slugify_filename(store_name)
    file_path = out_path / f"{seq_no:04d}_{safe_name}.json"

    file_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(file_path)


def main() -> None:
    parser = argparse.ArgumentParser(description="맛집 URL 정보를 바탕으로 다이닝코드 리뷰 및 이미지 추출")
    BASE_DIR = Path(__file__).resolve().parent.parent
    parser.add_argument("--input", default=str(BASE_DIR / "data" / "raw_store_data.csv"), help="앞 단계에서 수집된 raw_store_data.csv 경로")
    parser.add_argument("--summary", default=str(BASE_DIR / "review_data" / "review_crawl_summary.csv"), help="요약 CSV 경로")
    parser.add_argument("--json-dir", default=str(BASE_DIR / "review_data" / "jsons"), help="리뷰 JSON 저장 폴더")
    parser.add_argument("--img-dir", default=str(BASE_DIR / "review_data" / "images"), help="리뷰 이미지 저장 폴더")
    parser.add_argument("--headful", action="store_true", help="브라우저 창을 보이게 실행")
    parser.add_argument("--limit", type=int, default=None, help="상위 N개만 테스트")
    
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"❌ 입력 파일이 없습니다: {input_path}")
        return

    df = pd.read_csv(input_path)
    if "store_url" not in df.columns:
        print("❌ 입력 파일에 'store_url' 컬럼이 없습니다.")
        return

    # 성공한 데이터만 대상
    if "status" in df.columns:
        df = df[df["status"] == "ok"].copy()

    if args.limit is not None:
        df = df.head(args.limit).copy()

    processed_urls = get_processed_urls(args.summary)
    
    # 요약 디렉터리 등은 없을 수 있으므로 생성
    Path(args.summary).parent.mkdir(parents=True, exist_ok=True)
    Path(args.img_dir).mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=not args.headful,
            slow_mo=300,
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            viewport={"width": 1440, "height": 2200},
            locale="ko-KR",
        )
        page = context.new_page()

        # 구글 광고(Vignette 등)로 인한 스크롤/클릭 방해 차단
        page.route("**/*", lambda route: route.abort() if any(domain in route.request.url for domain in ["googleads", "googlesyndication", "doubleclick"]) else route.continue_())


        total = len(df)
        for idx, row in df.iterrows():
            store_url = str(row["store_url"]).strip()
            store_name = str(row.get("store_name", f"store_{idx}")).strip()

            if store_url in processed_urls:
                print(f"[{idx + 1}/{total}] ⏭️ 이미 처리됨: {store_name}")
                continue

            one = crawl_one_store_reviews(page, store_url, store_name, args.img_dir)
            
            json_path = ""
            if one.get("status") == "ok":
                json_path = save_store_reviews_json(one, args.json_dir, idx + 1)
                
            summary_row = {
                "store_name": store_name,
                "store_url": store_url,
                "status": one["status"],
                "skip_reason": one["skip_reason"],
                "review_count": one["review_count"],
                "json_path": json_path,
            }
            append_summary_csv(summary_row, args.summary)
            processed_urls.add(store_url)
            
            pause(1.2, 2.0)
            
        browser.close()

if __name__ == "__main__":
    main()
