import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path("c:/dev/Project/SK-Connect/etl/meal")
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from playwright.sync_api import sync_playwright
from meal_detail.raw.collect_details import crawl_one

def test_crawl():
    candidate = {
        "store_name": "Test Store",
        "store_url": "https://www.diningcode.com/profile.php?rid=zLIq0MCtK9dW"
    }
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            extra_http_headers={
                "Referer": "https://www.google.com/",
                "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7"
            }
        )
        page = context.new_page()
        
        print("Starting crawl with improved headers...")
        result = crawl_one(page, candidate)
        print("Result:", result)
        
        browser.close()

if __name__ == "__main__":
    test_crawl()
