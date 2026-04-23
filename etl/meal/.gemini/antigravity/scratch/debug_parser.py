import json
from bs4 import BeautifulSoup

html_path = r"C:/dev/Project/SK-Connect/etl/meal/diningcode_real_lake/crawling=raw/service=shop/year=2026/month=04/day=23/status=success/121304_e50478.html"

try:
    with open(html_path, 'r', encoding='utf-8') as f:
        html = f.read()

    soup = BeautifulSoup(html, 'html.parser')
    
    print("--- [Debug Start] ---")
    
    # 1. JSON-LD 찾기
    ld_tag = soup.find('script', type='application/ld+json')
    if not ld_tag:
        print("FAIL: JSON-LD tag not found!")
    else:
        print(f"SUCCESS: JSON-LD tag found. Content length: {len(ld_tag.get_text())}")
        
        # 2. JSON 파싱
        try:
            data = json.loads(ld_tag.get_text())
            print(f"SUCCESS: JSON parsed. Keys: {list(data.keys())}")
            
            # 3. 주소 확인
            addr = data.get("address")
            print(f"DEBUG: Address field: {addr} (type: {type(addr)})")
            
            if isinstance(addr, dict):
                print(f"DEBUG: streetAddress: {addr.get('streetAddress')}")
        except Exception as e:
            print(f"FAIL: JSON parsing error: {e}")

    # 4. Fallback Selector 확인
    print("\n--- [Fallback Check] ---")
    fallbacks = [".addr", ".address", "li.addr", "span.addr", ".btxt.area"]
    for sel in fallbacks:
        tag = soup.select_one(sel)
        if tag:
            print(f"SELECTOR '{sel}' FOUND: {tag.get_text(strip=True)}")
        else:
            print(f"SELECTOR '{sel}' NOT FOUND")

except Exception as e:
    print(f"CRITICAL ERROR: {e}")
