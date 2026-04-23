import os, sys
from bs4 import BeautifulSoup
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

raw_dir = "diningcode_real_lake/crawling=raw/service=shop/year=2026/month=04/day=23/status=success"
files = sorted(os.listdir(raw_dir), key=lambda x: os.path.getmtime(os.path.join(raw_dir, x)), reverse=True)
html_path = os.path.join(raw_dir, files[0])

with open(html_path, "r", encoding="utf-8") as f:
    soup = BeautifulSoup(f.read(), "html.parser")

reviews = soup.select(".s-list.blog-review, .near_review, .latter-graph, .person-review")
print(f"Total reviews: {len(reviews)}")
if reviews:
    print(reviews[0].prettify()[:2000])
