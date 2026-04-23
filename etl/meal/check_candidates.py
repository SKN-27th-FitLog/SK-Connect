import json, glob

files = sorted(glob.glob(r'diningcode_real_lake\process=candidate\**\*.jsonl', recursive=True))
f = files[-1]
print(f'File: {f}')
lines = open(f, encoding='utf-8').readlines()
print(f'Total candidates: {len(lines)}')

seen = set()
for i, line in enumerate(lines):
    d = json.loads(line)
    shop = d.get('shop', {})
    name = shop.get('name', '?')
    lat = shop.get('latitude', 0)
    lng = shop.get('longitude', 0)
    rating = shop.get('rating', 0)
    url = shop.get('canonical_url', '')
    menus_count = len(d.get('menus', []))
    reviews_count = len(d.get('reviews', []))
    images_count = len(d.get('images', []))
    print(f'  [{i}] {name} | lat={lat} lng={lng} rating={rating} | menus={menus_count} reviews={reviews_count} images={images_count} | {url}')
    seen.add(name)

print(f'\nUnique names: {len(seen)}')
