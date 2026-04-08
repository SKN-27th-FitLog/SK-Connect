"""
GeekNews 메인 페이지(https://news.hada.io/) HTML에서 토픽 행을 파싱해 최대 N건 CSV로 저장.
`--limit`이 한 페이지(약 20건)를 넘으면 `?page=2`, `?page=3` … 순으로 이어서 요청한다.
MCP(list_network_requests)로 확인 시 목록용 XHR/JSON은 없고 문서 HTML에 topic_row가 SSR 됨.

DOM 대응 선택자(참고):
    - 행: div.topic_row
    - 순위: div.votenum
    - 긱뉴스 토픽 ID: span[id^=vote] → vote28246
    - 제목 링크: div.topictitle > a (외부 URL 또는 topic?id=)
    - 도메인 표시: span.topicurl
    - 요약 링크: div.topicdesc > a[href^=topic?id=]
    - 메타: div.topicinfo (points, user, 상대시간, 댓글 링크)

CSV 열: time_text(원문), posted_at(상대시각 역산 ISO8601 KST; 미매칭 시 collected_at과 동일), collected_at(수집 시작 시각).

사용 예:
    python gatter_thread_geeknews.py
    python gatter_thread_geeknews.py --limit 10 -o thread_geeknews.csv
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
import urllib.error
import urllib.request
from collections.abc import Callable
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse
from zoneinfo import ZoneInfo

_KST = ZoneInfo("Asia/Seoul")

# 목록 상대시각 → timedelta(n). 달/개월은 달력월이 아닌 30일 근사, 년은 365일 근사(윤년 미반영).
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

# request에서 요청 시 유저 기기를 지정하는 고정 변수값 
# 일부 사이트는 기본 UA를 거부하므로 필요 시 문자열·헤더(Referer 등)를 바꿔서 시도할 수 있음.
_DEFAULT_USER_AGENT = "Mozilla/5.0 (compatible; it-threads-sample/1.0)"

# request로 파싱할 유저 정보 가져옴 
def _fetch_text(url: str, timeout: float, *, user_agent: str = _DEFAULT_USER_AGENT) -> str:
    """GET 요청으로 HTML/텍스트 본문만 가져옴. 리다이렉트·쿠키·재시도는 여기서 확장."""
    req = urllib.request.Request(url, headers={"User-Agent": user_agent})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", errors="replace")


# 여러 dict를 csv 파일로 저장하는 함수 
def _write_dict_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    """fieldnames 순서대로 열을 고정하고, dict에만 있는 키는 무시(extrasaction). Excel 호환을 위해 utf-8-sig."""
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


# ---------------------------------------------------------------------------
# GeekNews HTML 파싱 전용
# ---------------------------------------------------------------------------
# 목록 한 페이지 URL·내부 토픽 링크를 만들 때 쓰는 호스트(환경별로 바꾸려면 여기만 수정).
LIST_URL = "https://news.hada.io/"
GEEKNEWS_ORIGIN = "https://news.hada.io"

# SSR HTML 한 블록(topic_row)을 통째로 매칭. 사이트 마크업이 바뀌면 패턴만 고치면 됨.
# 캡처 그룹 순서: votenum, voteId, titleHref, title, domainLabel, descText, points,
# userId, userName, timeText, commentsHref, commentCell
_ROW_RE = re.compile(
    r"<div class='topic_row'><div class=votenum>(\d+)</div>"
    r".*?id='vote(\d+)'"
    r".*?<div class=topictitle><a href='([^']*)'[^>]*><h1>([^<]+)</h1></a> <span class=topicurl>\(([^)]*)\)</span>"
    r".*?<div class='topicdesc'><a href='topic\?id=\2'[^>]*>(.*?)</a></div>"
    r"<div class='topicinfo'><span id='tp\d+'>(\d+)</span> points? by <a href='/user\?id=([^']+)'>([^<]+)</a>\s*([^<]*?)<span id='unvote\d+'></span>\s*\|\s*<a href='([^']*)'[^>]*>([^<]+)</a>",
    re.DOTALL,
)


def parse_comment_count(comment_cell: str) -> str:
    """목록 셀 텍스트에서 숫자만 뽑거나, '댓글 없음' 류는 빈 문자열로 통일. 문구 변경 시 정규식/분기만 조정."""
    comment_cell = comment_cell.strip()
    m = re.search(r"댓글\s*(\d+)\s*개", comment_cell)
    if m:
        return m.group(1)
    if "댓글과 토론" in comment_cell:
        return 0 # 기존에는 ''을 리턴해서 None을 만들었는데 테이블을 채우기 위해 0으로 개수 리턴하도록 변경 
    return comment_cell


def geeknews_topic_url(topic_id: str) -> str:
    """긱뉴스 내부 토픽 페이지 URL. CSV의 article_url 등에 사용."""
    return f"{GEEKNEWS_ORIGIN}/topic?id={topic_id}"


def list_url_for_page(base_url: str, page: int) -> str:
    """목록 베이스 URL에 page 쿼리만 갱신·추가(나머지 쿼리 유지). 메인 피드는 ?page=N."""
    p = urlparse(base_url.strip())
    path = p.path if p.path else "/"
    q = parse_qs(p.query, keep_blank_values=True)
    q["page"] = [str(page)]
    query = urlencode(q, doseq=True)
    return urlunparse((p.scheme, p.netloc, path, "", query, p.fragment))


def parse_page_rows(html: str, *, collected_at: datetime) -> list[dict]:
    """한 페이지 HTML에서 topic_row를 모두 순서대로 파싱. collected_at은 상대시각 역산·미매칭 시 posted_at 기준."""
    collected_iso = collected_at.isoformat()
    rows: list[dict] = []
    for m in _ROW_RE.finditer(html):
        (
            rank,
            topic_id,
            title_href,
            title,
            domain_label,
            desc_text,
            points,
            user_id,
            user_name,
            time_text,
            _comments_href,
            comment_cell,
        ) = m.groups()

        title = re.sub(r"\s+", " ", title).strip()
        desc_text = re.sub(r"\s+", " ", desc_text).strip()
        time_text = time_text.strip()
        article_url = geeknews_topic_url(topic_id)
        ext = title_href.strip()
        if ext.startswith("topic?"):
            ext = ""

        rows.append(
            {
                "rank": rank,
                "topic_id": topic_id,
                "title": title,
                "article_url": article_url,
                "external_url": ext,
                "source_domain_label": domain_label.strip(),
                "excerpt": desc_text[:500] if desc_text else "",
                "points": points,
                "author_user_id": user_id,
                "author_display_name": user_name.strip(),
                "time_text": time_text,
                "posted_at": geeknews_relative_to_posted_at(time_text, collected_at),
                "collected_at": collected_iso,
                "comment_count": parse_comment_count(comment_cell),
            }
        )
    return rows


def main() -> int:
    """CLI 진입점: 목록 ?page= 루프로 fetch → parse → CSV. 실패 시 stderr에 이유만 남기고 비제로 종료."""
    p = argparse.ArgumentParser(description="GeekNews 메인 목록 샘플 → thread_geeknews.csv")
    p.add_argument("--url", default=LIST_URL, help="목록 페이지 베이스 URL (page 쿼리는 자동 설정)")
    p.add_argument("--limit", type=int, default=500)
    p.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="출력 CSV (기본: 이 폴더/thread_geeknews.csv)",
    )
    p.add_argument("--timeout", type=float, default=60.0)
    p.add_argument(
        "--max-pages",
        type=int,
        default=500,
        help="비정상 응답 시 무한 루프 방지용 최대 페이지 수(기본 500)",
    )
    args = p.parse_args()
    out = args.output or Path(__file__).resolve().parent / "thread_geeknews.csv"
    base_url = args.url
    limit = max(0, args.limit)
    max_pages = max(1, args.max_pages)

    rows: list[dict] = []
    page = 1
    stop_reason = ""
    collected_at = datetime.now(_KST)

    while len(rows) < limit and page <= max_pages:
        page_url = list_url_for_page(base_url, page)
        try:
            html = _fetch_text(page_url, args.timeout)
        except urllib.error.HTTPError as e:
            print(f"HTTP {e.code}: page={page} {page_url}", file=sys.stderr)
            return 1
        except OSError as e:
            print(f"{type(e).__name__}: page={page} {page_url} — {e}", file=sys.stderr)
            return 1

        batch = parse_page_rows(html, collected_at=collected_at)
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
        print("topic_row 파싱 결과가 없습니다. HTML 구조 변경 여부를 확인하세요.", file=sys.stderr)
        return 1

    print(f"stopped: {stop_reason}")
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
    print(len(rows), "rows ->", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
