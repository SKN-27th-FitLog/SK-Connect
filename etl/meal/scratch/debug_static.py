import requests
url = 'https://www.diningcode.com/profile.php?rid=0GPeI86zzPlD'
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36'}
r = requests.get(url, headers=headers)
with open('debug_static.html', 'w', encoding='utf-8') as f:
    f.write(r.text)
print(f"Status: {r.status_code}")
print(f"Length: {len(r.text)}")
