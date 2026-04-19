"""
PyTorchKR Discourse 카테고리 JSON에서 토픽 최대 N건을 it_thread 스타일 CSV로 저장.
`--limit`이 한 페이지 토픽 수를 넘으면 `?page=2`, `?page=3` … 순으로 이어서 요청한다.
"""
from __future__ import annotations

import argparse
import csv
import json
import logging
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

######################
# 스테이지 공통 설정 로딩 경로 보정 관련
######################
SCRIPT_STAGE_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_STAGE_ROOT) not in sys.path:
    sys.path.append(str(SCRIPT_STAGE_ROOT))

from common.settings import get_config

######################
# 설정 기반 상수 관련
######################
CONFIG = get_config()
SOURCE_CONFIG = CONFIG["sources"]["pytorch"]["thread"]
CSV_ENCODING = CONFIG["paths"]["csv_encoding"]
_DEFAULT_USER_AGENT = SOURCE_CONFIG["user_agent"]
logger = logging.getLogger(__name__)


def _fetch_json(url: str, timeout: float, *, user_agent: str = _DEFAULT_USER_AGENT) -> Any:
    """Discourse 카테고리 JSON을 GET 요청으로 받아 파이썬 객체로 변환한다."""
    req = urllib.request.Request(url, headers={"User-Agent": user_agent})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def _write_dict_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    """수집 결과를 설정된 CSV 인코딩 규칙으로 기록한다."""
    with path.open("w", encoding=CSV_ENCODING, newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


BASE = SOURCE_CONFIG["base_url"]
DEFAULT_JSON = SOURCE_CONFIG["json_url"]


def topic_url(slug: str, topic_id: int) -> str:
    """토픽 slug와 id를 조합해 브라우저용 토픽 URL을 만든다."""
    return f"{BASE}/t/{slug}/{topic_id}"


def list_url_for_page(base_url: str, page: int) -> str:
    """page 쿼리를 덮어쓴 카테고리 JSON URL을 생성한다."""
    p = urlparse(base_url.strip())
    path = p.path if p.path else "/"
    q = parse_qs(p.query, keep_blank_values=True)
    q["page"] = [str(page)]
    query = urlencode(q, doseq=True)
    return urlunparse((p.scheme, p.netloc, path, "", query, p.fragment))


def topics_from_payload(data: Any) -> list[dict]:
    """Discourse payload에서 실제 topic 목록만 안전하게 추출한다."""
    if not isinstance(data, dict):
        return []
    raw = (data.get("topic_list") or {}).get("topics")
    if not isinstance(raw, list):
        return []
    return [item for item in raw if isinstance(item, dict)]


def row_from_topic(topic: dict, category_slug: str) -> dict:
    """Discourse 토픽 객체를 thread CSV 한 행 구조로 정규화한다."""
    tid = topic.get("id")
    slug = topic.get("slug") or ""
    replies = topic.get("reply_count")
    if replies is None:
        replies = max(0, (topic.get("posts_count") or 1) - 1)

    tags = topic.get("tags") or []
    tag_parts: list[str] = []
    if isinstance(tags, list):
        for value in tags:
            if isinstance(value, str):
                tag_parts.append(value)
            elif isinstance(value, dict) and value.get("name"):
                tag_parts.append(str(value["name"]))

    return {
        "topic_id": tid,
        "title": (topic.get("title") or "").replace("\n", " ").strip(),
        "topic_url": topic_url(slug, tid) if tid else "",
        "slug": slug,
        "views": topic.get("views", ""),
        "reply_count": replies,
        "last_posted_at": topic.get("last_posted_at") or "",
        "bumped_at": topic.get("bumped_at") or "",
        "created_at": topic.get("created_at") or "",
        "last_poster_username": topic.get("last_poster_username") or "",
        "tags": "|".join(tag_parts),
        "category_slug": category_slug,
    }


def main() -> int:
    """PyTorch 카테고리 JSON을 페이지 단위로 순회해 thread CSV를 생성한다."""
    p = argparse.ArgumentParser(description="Discourse 카테고리 샘플 → thread_pytorch.csv")
    p.add_argument("--json-url", default=DEFAULT_JSON, help="카테고리 .json 베이스 URL (page 쿼리는 자동 설정)")
    p.add_argument("--limit", type=int, default=CONFIG["thread_collection"]["limit"], help="최대 행 수")
    p.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="출력 CSV (기본: 이 폴더/thread_pytorch.csv)",
    )
    p.add_argument("--category-slug", default=SOURCE_CONFIG["category_slug"], help="스키마용 카테고리 슬러그 메타")
    p.add_argument("--timeout", type=float, default=CONFIG["thread_collection"]["timeout"])
    p.add_argument("--max-pages", type=int, default=SOURCE_CONFIG["max_pages"], help="비정상 응답 시 최대 페이지 수")
    args = p.parse_args()

    out = args.output or Path(__file__).resolve().parent / SOURCE_CONFIG["default_output"]
    limit = max(0, args.limit)
    max_pages = max(1, args.max_pages)

    rows: list[dict] = []
    page = 1
    stop_reason = ""

    while len(rows) < limit and page <= max_pages:
        page_url = list_url_for_page(args.json_url, page)
        try:
            data = _fetch_json(page_url, args.timeout)
        except urllib.error.HTTPError as e:
            logger.error("HTTP %s: page=%s %s", e.code, page, page_url)
            return 1
        except OSError as e:
            logger.error("%s: page=%s %s - %s", type(e).__name__, page, page_url, e)
            return 1
        except json.JSONDecodeError as e:
            logger.error("JSONDecodeError: page=%s %s - %s", page, page_url, e)
            return 1

        batch = [row_from_topic(topic, args.category_slug) for topic in topics_from_payload(data)]
        for item in batch:
            rows.append(item)
            if len(rows) >= limit:
                stop_reason = f"reached limit {limit}"
                break
        logger.info("page=%s fetched %s rows (total %s, limit=%s)", page, len(batch), len(rows), limit)

        if not batch:
            stop_reason = f"no more rows at page {page} (total {len(rows)})"
            break
        if len(rows) >= limit:
            break
        page += 1

    if not stop_reason and page > max_pages:
        stop_reason = f"max-pages {max_pages} reached (total {len(rows)})"

    if not rows:
        logger.error("topic_list.topics 파싱 결과가 없습니다. JSON URL·형식 변경 여부를 확인하세요.")
        return 1

    logger.info("stopped: %s", stop_reason)
    fieldnames = [
        "topic_id",
        "title",
        "topic_url",
        "slug",
        "views",
        "reply_count",
        "last_posted_at",
        "bumped_at",
        "created_at",
        "last_poster_username",
        "tags",
        "category_slug",
    ]
    _write_dict_csv(out, fieldnames, rows)
    logger.info("%s rows -> %s", len(rows), out)
    return 0


def configure_logging() -> None:
    """진입점 기본 로깅 설정을 INFO 수준으로 초기화한다."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")


if __name__ == "__main__":
    configure_logging()
    raise SystemExit(main())
