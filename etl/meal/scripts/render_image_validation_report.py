import argparse
import json
from html import escape
from pathlib import Path
from typing import Any, Iterable, Sequence


KEEP_CLASS = "image-card image-card--keep"
DROP_CLASS = "image-card image-card--drop"


def render_report(input_path: str | Path, output_path: str | Path) -> None:
    records = list(_read_jsonl(Path(input_path)))
    html = _render_html(records)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(html, encoding="utf-8")


def _read_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as file:
        for line in file:
            if line.strip():
                yield json.loads(line)


def _render_html(records: list[dict[str, Any]]) -> str:
    sections = "\n".join(_render_restaurant_section(record) for record in records)
    return f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Image Validation Report</title>
  <style>
    body {{
      margin: 0;
      background: #f6f7f9;
      color: #1f2933;
      font-family: Arial, Helvetica, sans-serif;
    }}
    main {{
      max-width: 1180px;
      margin: 0 auto;
      padding: 24px;
    }}
    h1 {{
      margin: 0 0 24px;
      font-size: 28px;
    }}
    section {{
      margin-bottom: 32px;
      padding: 20px;
      background: #ffffff;
      border: 1px solid #d9dee7;
      border-radius: 8px;
    }}
    h2 {{
      margin: 0 0 16px;
      font-size: 22px;
    }}
    .image-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
      gap: 14px;
    }}
    .image-card {{
      display: flex;
      flex-direction: column;
      gap: 10px;
      padding: 12px;
      border: 2px solid;
      border-radius: 8px;
      background: #ffffff;
      overflow-wrap: anywhere;
    }}
    .image-card--keep {{
      border-color: #1f9d55;
    }}
    .image-card--drop {{
      border-color: #d64545;
    }}
    .image-card__status {{
      font-weight: 700;
      letter-spacing: 0;
    }}
    img {{
      width: 100%;
      aspect-ratio: 4 / 3;
      object-fit: cover;
      background: #eef1f5;
      border-radius: 6px;
    }}
    dl {{
      display: grid;
      grid-template-columns: 96px minmax(0, 1fr);
      gap: 6px 10px;
      margin: 0;
      font-size: 13px;
      line-height: 1.45;
    }}
    dt {{
      color: #5f6b7a;
      font-weight: 700;
    }}
    dd {{
      margin: 0;
    }}
  </style>
</head>
<body>
  <main>
    <h1>Image Validation Report</h1>
    {sections}
  </main>
</body>
</html>
"""


def _render_restaurant_section(record: dict[str, Any]) -> str:
    restaurant_name = _restaurant_name(record)
    keep_cards = "".join(_render_image_card(image, status="KEEP") for image in record.get("images", []))
    drop_cards = "".join(
        _render_image_card(image, status="DROP") for image in record.get("dropped_images", [])
    )
    cards = keep_cards + drop_cards
    return f"""<section>
  <h2>{escape(restaurant_name)}</h2>
  <div class="image-grid">
    {cards}
  </div>
</section>"""


def _restaurant_name(record: dict[str, Any]) -> str:
    store = record.get("store")
    if isinstance(store, dict) and store.get("name"):
        return str(store["name"])

    shop = record.get("shop")
    if isinstance(shop, dict) and shop.get("name"):
        return str(shop["name"])

    return str(record.get("entity_id") or "Unknown Restaurant")


def _render_image_card(image: dict[str, Any], status: str) -> str:
    validation = image.get("validation")
    if not isinstance(validation, dict):
        validation = {}

    url = str(image.get("url") or "")
    css_class = KEEP_CLASS if status == "KEEP" else DROP_CLASS
    rows = {
        "Group ID": validation.get("group_id"),
        "Group Order": validation.get("group_order"),
        "Nearest": validation.get("nearest_similarity"),
        "Reason": validation.get("reason"),
        "Original URL": url,
    }
    detail_rows = "\n".join(_render_detail_row(label, value) for label, value in rows.items())
    escaped_url = escape(url, quote=True)

    return f"""<article class="{css_class}">
  <div class="image-card__status">{status}</div>
  <img src="{escaped_url}" alt="{status} image">
  <dl>
    {detail_rows}
  </dl>
</article>"""


def _render_detail_row(label: str, value: Any) -> str:
    display_value = "" if value is None else str(value)
    return f"<dt>{escape(label)}</dt><dd>{escape(display_value)}</dd>"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render meal image validation JSONL as an HTML report.")
    parser.add_argument("--input", required=True, help="Image validation JSONL input path.")
    parser.add_argument("--output", required=True, help="HTML report output path.")
    args = parser.parse_args(argv)

    render_report(args.input, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
