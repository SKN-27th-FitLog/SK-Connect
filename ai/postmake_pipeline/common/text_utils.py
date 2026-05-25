def parse_keywords(value) -> list[str]:
    """Parse a row or raw keywords value into a clean keyword list."""
    if isinstance(value, dict):
        value = value.get("keywords") or ""
    if isinstance(value, str):
        return [keyword.strip() for keyword in value.split("#") if keyword.strip()]
    if isinstance(value, list):
        return [str(keyword).strip() for keyword in value if str(keyword).strip()]
    return []


def latest_crawling_created_at(rows: list[dict]) -> str:
    """Return the latest crawling timestamp string from analysis/crawling rows."""
    return max(
        (
            str(row.get("crawling_created_at") or row.get("created_dt") or "")
            for row in rows
            if row
        ),
        default="",
    )
