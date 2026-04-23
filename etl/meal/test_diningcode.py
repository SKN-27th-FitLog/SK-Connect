import asyncio
import json
import sys
import io
from src.collectors.platforms.diningcode_collector import DiningCodeCollector
from src.services.parsers.diningcode_parser import DiningCodeParser

# 한글 출력 설정
sys.stdout = io.TextIOWrapper(sys.stdout.detach(), encoding = 'utf-8')

async def test_single_url():
    # 브라우저 에이전트가 찾아낸 실시간 유효 URL
    target_url = "https://www.diningcode.com/profile.php?rid=6kwFNnBE61Hm"
    
    print(f"[*] Starting FINAL test for DiningCode: {target_url}")
    
    collector = DiningCodeCollector()
    raw_data = await collector.collect(target_url)
    
    # 디버깅용 HTML 저장
    with open("debug.html", "w", encoding="utf-8") as f:
        f.write(raw_data["raw_content"])
    
    parser = DiningCodeParser()
    shop = parser.parse_shop(raw_data["raw_content"])
    menus = parser.parse_menus(raw_data["raw_content"])
    reviews = parser.parse_reviews(raw_data["raw_content"])
    
    result = {
        "플랫폼": "DiningCode",
        "가게명": shop["name"],
        "설명(태그)": shop["description"],
        "주소": shop["full_address"],
        "메뉴수": len(menus),
        "메뉴샘플": menus[:2],
        "리뷰수": len(reviews),
        "리뷰샘플(작성일 포함)": {
            "작성자": reviews[0]["author"],
            "작성일": reviews[0]["visited_at"],
            "키워드": reviews[0]["keywords"],
            "내용": reviews[0]["content"][:100] + "..."
        } if reviews else "None"
    }
    
    print("\n[=== 최종 수집 결과 확인 ===]")
    print(json.dumps(result, indent=4, ensure_ascii=False))

if __name__ == "__main__":
    asyncio.run(test_single_url())
