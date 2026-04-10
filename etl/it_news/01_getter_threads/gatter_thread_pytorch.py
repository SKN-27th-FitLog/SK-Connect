"""
PyTorchKR Discourse 카테고리 JSON에서 토픽 최대 N건을 it_thread 스타일 CSV로 저장.
`--limit`이 한 페이지 토픽 수를 넘으면 `?page=2`, `?page=3` … 순으로 이어서 요청한다.

엔드포인트: https://discuss.pytorch.kr/c/news/14.json (브라우저 목록과 동일 데이터)

사용 예:
    python gatter_thread_pytorch.py
    python gatter_thread_pytorch.py --limit 10 -o thread_pytorch.csv
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

# Discourse JSON API는 보통 단순 GET이면 되나, 403 시 UA·Accept 헤더를 조정하는 식으로 확장 가능.
_DEFAULT_USER_AGENT = "Mozilla/5.0 (compatible; it-thread-sample/1.0)"


def _fetch_json(url: str, timeout: float, *, user_agent: str = _DEFAULT_USER_AGENT) -> Any:
    """응답 바이트를 UTF-8로 디코드한 뒤 json.loads. 페이지네이션은 URL의 ?page= 로 별도 호출이 일반적."""
    req = urllib.request.Request(url, headers={"User-Agent": user_agent})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())

def _write_dict_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    """열 순서는 fieldnames 고정. dict에만 있는 추가 키는 무시. utf-8-sig는 Excel에서 한글 열 때 유리."""
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)

# 다른 Discourse 인스턴스·카테고리를 쓰려면 BASE와 DEFAULT_JSON(또는 --json-url)만 바꾸면 됨.
BASE = "https://discuss.pytorch.kr"
DEFAULT_JSON = f"{BASE}/c/news/14.json"


def topic_url(slug: str, topic_id: int) -> str:
    """Discourse 표준 토픽 URL 패턴 /t/{slug}/{id}. slug가 비어도 id만으로 대개 동작."""
    return f"{BASE}/t/{slug}/{topic_id}"


def list_url_for_page(base_url: str, page: int) -> str:
    """카테고리 .json 베이스 URL에 page 쿼리만 갱신·추가(나머지 쿼리 유지). Discourse는 ?page=N."""
    p = urlparse(base_url.strip())
    path = p.path if p.path else "/"
    q = parse_qs(p.query, keep_blank_values=True)
    q["page"] = [str(page)]
    query = urlencode(q, doseq=True)
    return urlunparse((p.scheme, p.netloc, path, "", query, p.fragment))


def topics_from_payload(data: Any) -> list[dict]:
    """카테고리 JSON 한 페이지에서 topic_list.topics[] 만 dict 원소로 추출."""
    if not isinstance(data, dict):
        return []
    raw = (data.get("topic_list") or {}).get("topics")
    if not isinstance(raw, list):
        return []
    return [x for x in raw if isinstance(x, dict)]


def row_from_topic(t: dict, category_slug: str) -> dict:
    """topic_list.topics[] 원소 하나를 CSV 한 행(dict)으로 평탄화. API 필드명이 바뀌면 여기만 수정."""
    tid = t.get("id")
    slug = t.get("slug") or ""
    # reply_count가 없으면 posts_count-1로 대략치(첫 글 제외). 정확한 정책이 필요하면 API 문서에 맞게 조정.
    replies = t.get("reply_count")
    if replies is None:
        replies = max(0, (t.get("posts_count") or 1) - 1)

    # tags는 문자열 리스트 또는 {name: ...} 객체 리스트 등 혼합 가능성에 대비.
    tags = t.get("tags") or []
    tag_parts: list[str] = []
    if isinstance(tags, list):
        for x in tags:
            if isinstance(x, str):
                tag_parts.append(x)
            elif isinstance(x, dict) and x.get("name"):
                tag_parts.append(str(x["name"]))
    tag_str = "|".join(tag_parts)

    return {
        "topic_id": tid,
        "title": (t.get("title") or "").replace("\n", " ").strip(),
        "topic_url": topic_url(slug, tid) if tid else "",
        "slug": slug,
        "views": t.get("views", ""),
        "reply_count": replies,
        "last_posted_at": t.get("last_posted_at") or "",
        "bumped_at": t.get("bumped_at") or "",
        "created_at": t.get("created_at") or "",
        "last_poster_username": t.get("last_poster_username") or "",
        "tags": tag_str,
        "category_slug": category_slug,
    }


def main() -> int:
    """CLI: ?page= 루프로 JSON을 가져와 상위 limit개까지 CSV로 저장."""
    p = argparse.ArgumentParser(description="Discourse 카테고리 샘플 → thread_pytorch.csv")
    p.add_argument(
        "--json-url",
        default=DEFAULT_JSON,
        help="카테고리 .json 베이스 URL (page 쿼리는 자동 설정)",
    )
    p.add_argument("--limit", type=int, default=500, help="최대 행 수")
    p.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="출력 CSV (기본: 이 폴더/thread_pytorch.csv)",
    )
    p.add_argument("--category-slug", default="news", help="스키마용 카테고리 슬러그 메타")
    p.add_argument("--timeout", type=float, default=60.0)
    p.add_argument(
        "--max-pages",
        type=int,
        default=500,
        help="비정상 응답 시 무한 루프 방지용 최대 페이지 수(기본 500)",
    )
    args = p.parse_args()
    out = args.output or Path(__file__).resolve().parent / "thread_pytorch.csv"
    base_url = args.json_url
    limit = max(0, args.limit)
    max_pages = max(1, args.max_pages)

    rows: list[dict] = []
    page = 1
    stop_reason = ""

    while len(rows) < limit and page <= max_pages:
        page_url = list_url_for_page(base_url, page)
        try:
            data = _fetch_json(page_url, args.timeout)
        except urllib.error.HTTPError as e:
            print(f"HTTP {e.code}: page={page} {page_url}", file=sys.stderr)
            return 1
        except OSError as e:
            print(f"{type(e).__name__}: page={page} {page_url} — {e}", file=sys.stderr)
            return 1
        except json.JSONDecodeError as e:
            print(f"JSONDecodeError: page={page} {page_url} — {e}", file=sys.stderr)
            return 1

        topic_dicts = topics_from_payload(data)
        batch = [row_from_topic(t, args.category_slug) for t in topic_dicts]
        for item in batch:
            rows.append(item)
            if len(rows) >= limit:
                stop_reason = f"reached limit {limit}"
                break
        print(f"page={page} fetched {len(batch)} rows (total {len(rows)}, limit={limit})")

        if not batch:
            stop_reason = f"no more rows at page {page} (total {len(rows)})"
            break
        if len(rows) >= limit:
            break
        page += 1

    if not stop_reason and page > max_pages:
        stop_reason = f"max-pages {max_pages} reached (total {len(rows)})"

    if not rows:
        print(
            "topic_list.topics 파싱 결과가 없습니다. JSON URL·형식 변경 여부를 확인하세요.",
            file=sys.stderr,
        )
        return 1

    print(f"stopped: {stop_reason}")
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
    print(len(rows), "rows ->", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
