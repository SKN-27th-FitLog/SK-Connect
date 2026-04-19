"""
GeekNews 메인 페이지(https://news.hada.io/) HTML에서 토픽 행을 파싱해 최대 N건 CSV로 저장.
`--limit`이 한 페이지(약 20건)를 넘으면 `?page=2`, `?page=3` … 순으로 이어서 요청한다.
MCP(list_network_requests)로 확인 시 목록용 XHR/JSON은 없고 문서 HTML에 topic_row가 SSR 됨.

DOM 대응 선택자(참고, 변경 시 _parse_topic_row_block 주석과 함께 점검):
    - 행: div.topic_row (data-topic-state-id 등 속성이 뒤에 붙을 수 있음 → 한 줄 정규식 매칭 대신 블록 분리)
    - 순위: div.votenum
    - 긱뉴스 토픽 ID: span[id^=vote] → vote28430
    - 제목: div.topictitle 안에 dead* span 뒤에 오는 첫 a + h1/h2, span.topicurl(도메인)
    - 요약: div.topicdesc > a (href는 topic?id=, /topic?id=, 절대 URL 등 변형 가능)
    - 메타: div.topicinfo — points, /user/{id} 형식 사용자 링크, 상대시각, 댓글 링크

CSV 열: time_text(원문), posted_at(상대시각 역산 ISO8601 KST; 미매칭 시 collected_at과 동일), collected_at(수집 시작 시각).

사용 예:
    python gatter_thread_geeknews.py
    python gatter_thread_geeknews.py --limit 10 -o thread_geeknews.csv
"""
from __future__ import annotations

import argparse
import csv
import logging
import re
import sys
import urllib.error
import urllib.request
from collections.abc import Callable
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse
from zoneinfo import ZoneInfo

######################
# 스테이지 공통 설정 로딩 경로 보정 관련
######################
# 단독 실행 시에도 `common.settings`를 읽을 수 있도록 스테이지 루트를 import path에 추가한다.
SCRIPT_STAGE_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_STAGE_ROOT) not in sys.path:
    sys.path.append(str(SCRIPT_STAGE_ROOT))

from common.settings import get_config

######################
# 설정 기반 상수 및 시간 규칙 관련
######################
CONFIG = get_config()
SOURCE_CONFIG = CONFIG["sources"]["geeknews"]["thread"]
CSV_ENCODING = CONFIG["paths"]["csv_encoding"]
_KST = ZoneInfo(CONFIG["timezone"])
logger = logging.getLogger(__name__)

# GeekNews 상대시각 문자열을 절대시각으로 역산하기 위한 규칙 테이블이다.
_TIME_RULES: list[tuple[re.Pattern[str], Callable[[int], timedelta]]] = [
    (re.compile(r"^(\d+)시간전$"), lambda n: timedelta(hours=n)),
    (re.compile(r"^(\d+)일전$"), lambda n: timedelta(days=n)),
    (re.compile(r"^(\d+)주전$"), lambda n: timedelta(weeks=n)),
    (re.compile(r"^(\d+)달전$"), lambda n: timedelta(days=30 * n)),
    (re.compile(r"^(\d+)개월전$"), lambda n: timedelta(days=30 * n)),
    (re.compile(r"^(\d+)년전$"), lambda n: timedelta(days=365 * n)),
]


def geeknews_relative_to_posted_at(time_text: str, collected_at: datetime) -> str:
    """상대시각 문자열을 collected_at 기준으로 역산한 ISO8601(+offset) 문자열. 패턴 불일치 시 collected_at."""
    if collected_at.tzinfo is None:
        raise ValueError("collected_at must be timezone-aware")
    s = time_text.strip()
    fallback = collected_at.isoformat()
    for pat, mk_delta in _TIME_RULES:
        m = pat.match(s)
        if m:
            n = int(m.group(1))
            return (collected_at - mk_delta(n)).isoformat()
    return fallback


_DEFAULT_USER_AGENT = SOURCE_CONFIG["user_agent"]


def _fetch_text(url: str, timeout: float, *, user_agent: str = _DEFAULT_USER_AGENT) -> str:
    """GET 요청으로 HTML/텍스트 본문만 가져온다."""
    req = urllib.request.Request(url, headers={"User-Agent": user_agent})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", errors="replace")


def _write_dict_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    """fieldnames 순서대로 열을 고정하고 CSV로 저장한다."""
    with path.open("w", encoding=CSV_ENCODING, newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


LIST_URL = SOURCE_CONFIG["list_url"]
GEEKNEWS_ORIGIN = SOURCE_CONFIG["origin"]
EXCERPT_MAX_CHARS = SOURCE_CONFIG["excerpt_max_chars"]

_TOPIC_ROW_BLOCK_RE = re.compile(
    r"<div\s+class\s*=\s*['\"]topic_row['\"][^>]*>.*?(?=<div\s+class\s*=\s*['\"]topic_row['\"][^>]*>|$)",
    re.DOTALL,
)
_TITLE_IN_ROW_RE = re.compile(
    r"<div\s+class\s*=\s*topictitle\s*>"
    r".*?<a\s+[^>]*href\s*=\s*(['\"])([^'\"]*)\1[^>]*>\s*<h[12]>([^<]+)</h[12]>\s*</a>\s*"
    r"<span[^>]*class\s*=\s*topicurl[^>]*>\(([^)]*)\)</span>",
    re.DOTALL | re.IGNORECASE,
)


def _parse_topic_row_block(block: str, *, collected_at: datetime) -> dict | None:
    """topic_row 한 블록에서 필요한 필드를 뽑는다."""
    m_rank = re.search(r"<div\s+class\s*=\s*votenum\s*>(\d+)</div>", block)
    m_vote = re.search(r"id\s*=\s*['\"]vote(\d+)['\"]", block)
    if not m_rank or not m_vote:
        return None
    rank, topic_id = m_rank.group(1), m_vote.group(1)

    m_title = _TITLE_IN_ROW_RE.search(block)
    if not m_title:
        return None
    title_href, title, domain_label = m_title.group(2), m_title.group(3), m_title.group(4)

    desc_re = re.compile(
        r"<div\s+class\s*=\s*['\"]topicdesc['\"]\s*>"
        r"<a[^>]*href\s*=\s*['\"](?:https?://news\.hada\.io)?/?topic\?id="
        + re.escape(topic_id)
        + r"(?:[^'\"]*)?['\"][^>]*>(.*?)</a>\s*</div>",
        re.DOTALL | re.IGNORECASE,
    )
    m_desc = desc_re.search(block)
    desc_text = re.sub(r"\s+", " ", m_desc.group(1)).strip() if m_desc else ""

    m_info = re.search(
        r"<div\s+class\s*=\s*['\"]topicinfo['\"]\s*>"
        r"<span\s+id\s*=\s*['\"]tp\d+['\"]>(\d+)</span>\s+points\s+by\s+"
        r"<a\s+href\s*=\s*['\"](?:/@|/user/)([^'\"]+)['\"]>([^<]+)</a>\s*"
        r"([^<]*?)<span\s+id\s*=\s*['\"]unvote\d+['\"]>\s*</span>\s*\|\s*"
        r"<a\s+[^>]*href\s*=\s*(['\"])([^'\"]*)\5[^>]*>([^<]+)</a>",
        block,
        re.DOTALL | re.IGNORECASE,
    )
    if not m_info:
        return None
    points, user_id, user_name, time_text, _q, _comments_href, comment_cell = m_info.groups()
    time_text = time_text.strip()

    collected_iso = collected_at.isoformat()
    article_url = geeknews_topic_url(topic_id)
    ext = title_href.strip()
    if ext.startswith("topic?") or ext.startswith("/topic?"):
        ext = ""

    return {
        "rank": rank,
        "topic_id": topic_id,
        "title": re.sub(r"\s+", " ", title).strip(),
        "article_url": article_url,
        "external_url": ext,
        "source_domain_label": domain_label.strip(),
        "excerpt": desc_text[:EXCERPT_MAX_CHARS] if desc_text else "",
        "points": points,
        "author_user_id": user_id,
        "author_display_name": user_name.strip(),
        "time_text": time_text,
        "posted_at": geeknews_relative_to_posted_at(time_text, collected_at),
        "collected_at": collected_iso,
        "comment_count": parse_comment_count(comment_cell),
    }


def parse_comment_count(comment_cell: str) -> str:
    """목록 셀 텍스트에서 댓글 개수를 추출한다."""
    comment_cell = comment_cell.strip()
    m = re.search(r"댓글\s*(\d+)\s*개", comment_cell)
    if m:
        return m.group(1)
    if "댓글과 토론" in comment_cell:
        return 0
    return comment_cell


def geeknews_topic_url(topic_id: str) -> str:
    """GeekNews 토픽 상세 페이지 URL을 생성한다."""
    return f"{GEEKNEWS_ORIGIN}/topic?id={topic_id}"


def list_url_for_page(base_url: str, page: int) -> str:
    """페이지 번호를 반영한 GeekNews 목록 URL을 생성한다."""
    p = urlparse(base_url.strip())
    path = p.path if p.path else "/"
    q = parse_qs(p.query, keep_blank_values=True)
    q["page"] = [str(page)]
    query = urlencode(q, doseq=True)
    return urlunparse((p.scheme, p.netloc, path, "", query, p.fragment))


def parse_page_rows(html: str, *, collected_at: datetime) -> list[dict]:
    """한 페이지 HTML에서 topic_row 블록들을 모두 파싱해 행 목록으로 반환한다."""
    rows: list[dict] = []
    for m in _TOPIC_ROW_BLOCK_RE.finditer(html):
        row = _parse_topic_row_block(m.group(0), collected_at=collected_at)
        if row:
            rows.append(row)
    return rows


def main() -> int:
    """GeekNews 목록을 페이지 단위로 순회해 thread CSV를 생성한다."""
    p = argparse.ArgumentParser(description="GeekNews 메인 목록 샘플 → thread_geeknews.csv")
    p.add_argument("--url", default=LIST_URL, help="목록 페이지 베이스 URL (page 쿼리는 자동 설정)")
    p.add_argument("--limit", type=int, default=CONFIG["thread_collection"]["limit"])
    p.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="출력 CSV (기본: 이 폴더/thread_geeknews.csv)",
    )
    p.add_argument("--timeout", type=float, default=CONFIG["thread_collection"]["timeout"])
    p.add_argument(
        "--max-pages",
        type=int,
        default=SOURCE_CONFIG["max_pages"],
        help="비정상 응답 시 무한 루프 방지용 최대 페이지 수(기본 500)",
    )
    args = p.parse_args()
    out = args.output or Path(__file__).resolve().parent / SOURCE_CONFIG["default_output"]
    base_url = args.url
    limit = max(0, args.limit)
    max_pages = max(1, args.max_pages)

    rows: list[dict] = []
    page = 1
    stop_reason = ""
    collected_at = datetime.now(_KST)

    # limit 또는 max_pages에 도달할 때까지 페이지를 늘려가며 누적 수집한다.
    while len(rows) < limit and page <= max_pages:
        page_url = list_url_for_page(base_url, page)
        try:
            html = _fetch_text(page_url, args.timeout)
        except urllib.error.HTTPError as e:
            logger.error("HTTP %s: page=%s %s", e.code, page, page_url)
            return 1
        except OSError as e:
            logger.error("%s: page=%s %s - %s", type(e).__name__, page, page_url, e)
            return 1

        batch = parse_page_rows(html, collected_at=collected_at)
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
        logger.error("topic_row 파싱 결과가 없습니다. HTML 구조 변경 여부를 확인하세요.")
        return 1

    logger.info("stopped: %s", stop_reason)
    fieldnames = [
        "rank",
        "topic_id",
        "title",
        "article_url",
        "external_url",
        "source_domain_label",
        "excerpt",
        "points",
        "author_user_id",
        "author_display_name",
        "time_text",
        "posted_at",
        "collected_at",
        "comment_count",
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
