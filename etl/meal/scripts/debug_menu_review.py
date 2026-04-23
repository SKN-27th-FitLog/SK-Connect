import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

path = "diningcode_real_lake/crawling=candidate/service=shop/year=2026/month=04/day=23/status=success/cand_diningcode_unknown_id.jsonl"
with open(path, "r", encoding="utf-8") as f:
    data = json.loads(f.readline())

print(f"=== 메뉴: {len(data.get('menus', []))}건 ===")
for m in data["menus"][:5]:
    print(f"  - {m['name']} ({m['price']}원)")
if len(data["menus"]) > 5:
    print(f"  ... 외 {len(data['menus'])-5}건")

print(f"\n=== 리뷰: {len(data.get('reviews', []))}건 ===")
for r in data["reviews"]:
    print(f"  - [{r['rating']}점] {r['content'][:60]}...")
