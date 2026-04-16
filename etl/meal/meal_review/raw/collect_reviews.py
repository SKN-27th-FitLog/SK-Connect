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
DATE_PATTERN: Final[re.Pattern] = re.compile(
    r"(\d{4}[.-]\d{1,2}[.-]\d{1,2})|"  # 2024.01.01 or 2024-01-01
    r"(\d{4}년\s*\d{1,2}월\s*\d{1,2}일)|" # 2024년 1월 1일
    r"(\d{1,2}월\s*\d{1,2}일)"          # 1월 1일 (올해)
)
SAFE_FILENAME_PATTERN: Final[re.Pattern] = re.compile(r"[^0-9a-zA-Z가-힣._-]+")

def format_date_standard(date_text: str) -> str:
    """다양한 날짜 형식을 YYYY-MM-DD로 정규화합니다."""
    if not date_text: return ""
    
    # 1. YYYY.MM.DD 또는 YYYY-MM-DD
    match = re.search(r"(\d{4})[.-](\d{1,2})[.-](\d{1,2})", date_text)
    if match:
        return f"{match.group(1)}-{match.group(2).zfill(2)}-{match.group(3).zfill(2)}"
    
    # 2. YYYY년 MM월 DD일
    match = re.search(r"(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일", date_text)
    if match:
        return f"{match.group(1)}-{match.group(2).zfill(2)}-{match.group(3).zfill(2)}"
        
    # 3. MM월 DD일 (연도 미표기 시 현재 연도 기준 가공 - 2026년)
    match = re.search(r"(\d{1,2})월\s*(\d{1,2})일", date_text)
    if match:
        return f"2026-{match.group(1).zfill(2)}-{match.group(2).zfill(2)}"
        
    return ""

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
    # [추가] '평가 더보기' 버튼이 있으면 클릭 (최소 1회)
    try:
        more_btn = page.locator("a:has-text('평가 더보기')")
        if more_btn.count() > 0:
            more_btn.first.click(timeout=3000)
            pause(1.0, 1.5)
    except Exception:
        pass

    for i in range(rounds):
        try:
            page.mouse.wheel(0, 4000)
            pause(0.8, 1.2)
        except Exception:
            break

def collect_reviews_structured(page: Page, store_name: str, max_items: int = 500) -> List[Dict[str, object]]:
    reviews: List[Dict[str, object]] = []
    seen: Set[tuple] = set()
    
    # [추가] 상세 내용 '...더보기' 모두 클릭하여 원본 텍스트 노출
    try:
        more_links = page.locator("a:has-text('...더보기')")
        m_count = more_links.count()
        for j in range(m_count):
            try:
                more_links.nth(j).click(timeout=1000)
                pause(0.1, 0.3)
            except Exception:
                pass
    except Exception:
        pass

    blocks: Locator = page.locator("div[id^='div_review_']")
    count: int = min(blocks.count(), max_items)

    for i in range(count):
        try:
            block: Locator = blocks.nth(i)
            review_id: str = block.get_attribute("id") or ""
            
            # [수정] 평점 선택자 강화 (.star-point, span.point 모두 시도)
            rating_text = ""
            for selector in [".star-point", "span.point", "p.person-grade"]:
                loc = block.locator(selector)
                if loc.count() > 0:
                    rating_text = safe_text(loc)
                    if rating_text: break
            
            rating = float(RATING_PATTERN.search(rating_text).group()) if RATING_PATTERN.search(rating_text) else 0.0
            
            # [수정] 날짜 선택자 강화 및 표준화 (YYYY-MM-DD)
            date_text = ""
            for selector in [".date", "span.date", ".person-conf .date"]:
                loc = block.locator(selector)
                if loc.count() > 0:
                    date_text = safe_text(loc)
                    if date_text: break
            
            date = format_date_standard(date_text)
            
            # [수정] 본문 선택자 강화 (.review_contents)
            content = safe_text(block.locator(".review_contents, p.review_contents"))
            if not content:
                logger.debug(f"Skipping empty review content: {review_id}")
                continue

            # [추가] 리뷰 이미지 URL 추출 로직
            img_locators = block.locator("img.review_img, .img_box img")
            image_urls: List[str] = []
            img_count = min(img_locators.count(), 10) # 최대 10장으로 상향
            for idx in range(img_count):
                src = img_locators.nth(idx).get_attribute("src")
                if src and src.startswith("http"):
                    image_urls.append(src)

            # 중복 체크 (Shadowing 방지)
            key: tuple = (content[:200], date, rating)
            if key in seen: continue
            seen.add(key)

            reviews.append({
                "review_id": review_id,
                "rating": rating,
                "date": date,
                "content": content,
                "image_urls": json.dumps(image_urls, ensure_ascii=False)
            })
        except Exception as e:
            logger.debug(f"Row skip: {e}")
            continue
    return reviews

def download_review_images(store_name: str, image_urls_json: str) -> List[str]:
    """
    [추가] 리뷰 이미지를 로컬 경로(review_data/images/{가게명}/)에 다운로드합니다.
    AWS 업로드 전 임시 보관 및 전수 수집 확인용입니다.
    """
    try:
        urls: List[str] = json.loads(image_urls_json)
    except Exception:
        return []
        
    local_paths: List[str] = []
    if not urls:
        return []

    # 저장 폴더 생성 (review_data/images/{가게명})
    target_dir: Path = get_project_root() / "review_data" / "images" / slugify_filename(store_name)
    target_dir.mkdir(parents=True, exist_ok=True)

    for i, url in enumerate(urls):
        try:
            ext: str = Path(url.split("?")[0]).suffix or ".jpg"
            save_name: str = f"rev_{int(time.time())}_{i}{ext}"
            save_path: Path = target_dir / save_name
            
            # 이미지 다운로드 (urllib 사용)
            urllib.request.urlretrieve(url, str(save_path))
            local_paths.append(str(save_path))
            pause(0.2, 0.4)
        except Exception as e:
            logger.warning(f"⚠️ 이미지 다운로드 실패: {url} ({str(e)})")
            
    return local_paths

# 수집 결과 데이터 컬럼 정의
REVIEW_OUTPUT_COLUMNS: Final[List[str]] = [
    "review_id", "rating", "date", "content", 
    "image_urls", "store_name", "store_url", "local_image_paths"
]

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
        user_agent: str = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
        )
        browser: Browser = p.chromium.launch(headless=not args.headful, slow_mo=300)
        context: BrowserContext = browser.new_context(user_agent=user_agent, locale="ko-KR")
        page: Page = context.new_page()

        all_review_results: List[Dict[str, object]] = []

        for _, row in df_stores.iterrows():
            url: str = str(row.get("store_url", "nan")).strip()
            name: str = str(row.get("store_name", "nan")).strip()
            
            # 유효하지 않은 URL 또는 데이터 스킵 로직
            if url == "nan" or not url.startswith("http"):
                logger.warning(f"⏩ 유효하지 않은 URL 스카핑 ({name}): {url}")
                continue
            
            logger.info(f"🚀 리뷰 수집 중: {name}")
            
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=60000)
                # 리뷰 블록이 하나라도 나타날 때까지 대기
                try:
                    page.wait_for_selector("div[id^='div_review_'], a:has-text('평가 더보기')", timeout=5000)
                except Exception:
                    logger.debug(f"Review container not found for {name}, skipping expansion")
                
                page.wait_for_timeout(1000)
                scroll_reviews(page)
                
                reviews: List[Dict[str, object]] = collect_reviews_structured(page, name)
                for rv in reviews:
                    local_img_paths = download_review_images(name, rv.get("image_urls", "[]"))
                    rv.update({
                        "store_name": name, 
                        "store_url": url,
                        "local_image_paths": json.dumps(local_img_paths, ensure_ascii=False)
                    })
                    all_review_results.append(rv)
            except Exception as e:
                logger.error(f"❌ 리뷰 수집 실패 ({name}): {str(e)}")

        browser.close()

    # [수정] 결과가 없더라도 항상 컬럼 헤더가 포함된 파일을 저장하여 파이프라인 중단 방지
    df_rv: pd.DataFrame = pd.DataFrame(all_review_results)
    for col in REVIEW_OUTPUT_COLUMNS:
        if col not in df_rv.columns:
            df_rv[col] = pd.Series(dtype=object)
    
    df_rv = df_rv[REVIEW_OUTPUT_COLUMNS]
    
    save_path: Path = get_hive_path("process=raw", "service=review", "success")
    df_rv.to_csv(save_path, index=False, encoding="utf-8-sig")
    
    if all_review_results:
        logger.info(f"✅ 리뷰 {len(df_rv)}건 수집 완료 (Hive/raw/review: {save_path.name})")
    else:
        logger.warning(f"💡 수집된 리뷰가 없지만 빈 파일을 생성했습니다: {save_path.name}")

if __name__ == "__main__":
    main()
