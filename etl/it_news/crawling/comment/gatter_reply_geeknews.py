from __future__ import annotations

import argparse
import csv
import os
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import psycopg


######################
# DB 연결 정보 구성 관련
######################
def _env(name: str, default: str) -> str:
    """
    환경 변수를 읽고 비어 있으면 기본값을 반환한다.

    Args:
        name: 환경 변수 이름.
        default: 기본값.

    Returns:
        환경 변수 값 또는 기본값.
    """
    value = os.environ.get(name)
    return value if value is not None and value != "" else default


def get_connection_params() -> dict[str, Any]:
    """
    psycopg 연결 인자를 환경 변수 기준으로 조립한다.

    Returns:
        PostgreSQL 연결 파라미터 딕셔너리.
    """
    return {
        "host": _env("PGHOST", "localhost"),
        "port": int(_env("PGPORT", "5432")),
        "dbname": _env("PGDATABASE", "service"),
        "user": _env("PGUSER", "user"),
        "password": _env("PGPASSWORD", "password"),
    }


def check_connection() -> psycopg.Connection:
    """
    DB 연결 가능 여부를 확인한 뒤 연결 객체를 반환한다.

    Returns:
        사용 가능한 psycopg 연결 객체.
    """
    params = get_connection_params()
    try:
        conn = psycopg.connect(**params, connect_timeout=10)
        conn.execute("SELECT 1")
        return conn
    except psycopg.Error as exc:
        print(f"DB 연결 실패: {exc}", file=sys.stderr)
        raise


_KST = ZoneInfo("Asia/Seoul")
_DEFAULT_USER_AGENT = "Mozilla/5.0 (compatible; it-threads-sample/1.0)"
_COMMENT_ROW_OPEN = re.compile(
    r"<div\s+class\s*=\s*(?:\"comment_row\"|'comment_row'|comment_row)\b[^>]*>",
    re.IGNORECASE,
)
_COMMENT_DATE = re.compile(
    r"href\s*=\s*[\"']comment\?id=\d+[\"']\s*>([^<]+)</a>",
    re.IGNORECASE,
)
_COMMENT_BODY = re.compile(
    r"comment_contents[^>]*>([\s\S]*?)</span>\s*</div>\s*<div\s+class\s*=\s*commentreply\b",
    re.IGNORECASE,
)
_FALLBACK_BODY = re.compile(r"comment_contents[^>]*>([\s\S]*?)</span>", re.IGNORECASE)
_DEFAULT_SLEEP_SECONDS = 0.75
_MAX_COMMENTS_PER_TOPIC = 500

SQL_GEEK_ROWS = """
SELECT crawling_id, article_url, thread
FROM crawling
WHERE thread ~ '^geek_'
  AND article_url IS NOT NULL
  AND trim(article_url) <> ''
ORDER BY crawling_id
"""


######################
# HTML → 텍스트 변환 및 댓글 파싱 관련
######################
class _HTMLToText(HTMLParser):
    """댓글 HTML 조각을 사람이 읽는 평문으로 바꾸기 위한 간단한 파서."""

    _BLOCK = frozenset({"p", "div", "br", "hr", "li", "ul", "ol", "h1", "h2", "h3", "h4", "h5", "h6", "tr", "pre", "code"})

    def __init__(self) -> None:
        """텍스트 조각 누적 버퍼를 초기화한다."""
        super().__init__(convert_charrefs=True)
        self._parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        """블록 태그 시작 시 공백 또는 줄바꿈을 추가한다."""
        if tag.lower() == "br":
            self._parts.append("\n")
        elif tag.lower() in self._BLOCK:
            self._parts.append(" ")

    def handle_endtag(self, tag: str) -> None:
        """블록 태그 종료 시 문단 경계를 보정한다."""
        if tag.lower() in self._BLOCK:
            self._parts.append(" ")

    def handle_data(self, data: str) -> None:
        """태그 사이 문자 데이터를 누적한다."""
        self._parts.append(data)

    def get_text(self) -> str:
        """누적한 조각을 하나의 문자열로 반환한다."""
        return "".join(self._parts)


def _html_fragment_to_plain(fragment: str) -> str:
    """
    댓글 본문 HTML 조각을 공백 정리된 평문으로 변환한다.

    Args:
        fragment: HTML 조각 문자열.

    Returns:
        공백 정리된 평문 문자열.
    """
    parser = _HTMLToText()
    try:
        parser.feed(fragment)
        parser.close()
    except Exception:
        return ""
    return re.sub(r"\s+", " ", parser.get_text()).strip()


def _fetch_text(url: str, timeout: float, *, user_agent: str = _DEFAULT_USER_AGENT) -> str:
    """
    댓글 수집 대상 토픽 HTML을 가져온다.

    Args:
        url: 가져올 페이지 URL.
        timeout: HTTP 타임아웃(초).
        user_agent: 요청 시 사용할 User-Agent.

    Returns:
        UTF-8 문자열로 디코드된 HTML 본문.
    """
    req = urllib.request.Request(url, headers={"User-Agent": user_agent})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="replace")


def _parse_date_loose(value: str) -> datetime | None:
    """
    GeekNews 댓글 날짜 문자열을 KST datetime으로 느슨하게 파싱한다.

    Args:
        value: 댓글 날짜 문자열.

    Returns:
        파싱된 datetime 또는 실패 시 None.
    """
    text = value.strip()
    for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(text, fmt).replace(tzinfo=_KST)
        except ValueError:
            continue
    return None


def iter_comment_row_blocks(html: str) -> list[str]:
    """
    토픽 HTML에서 개별 댓글 블록을 순서대로 분리한다.

    Args:
        html: 토픽 페이지 HTML 문자열.

    Returns:
        개별 댓글 블록 문자열 목록.
    """
    starts = [match.start() for match in _COMMENT_ROW_OPEN.finditer(html)]
    blocks: list[str] = []
    for index, start in enumerate(starts):
        end = starts[index + 1] if index + 1 < len(starts) else len(html)
        blocks.append(html[start:end])
    return blocks


def parse_comments_from_topic_html(html: str, *, max_comments: int) -> list[tuple[str, str]]:
    """
    토픽 HTML에서 댓글 생성 시각과 본문을 추출한다.

    Args:
        html: 토픽 페이지 HTML 문자열.
        max_comments: 토픽당 최대 댓글 수.

    Returns:
        (created_at, content) 튜플 목록.
    """
    out: list[tuple[str, str]] = []
    now_iso = datetime.now(_KST).isoformat()
    for block in iter_comment_row_blocks(html):
        if len(out) >= max_comments:
            break
        match_date = _COMMENT_DATE.search(block)
        date_text = match_date.group(1).strip() if match_date else ""
        parsed = _parse_date_loose(date_text) if date_text else None
        created_iso = parsed.isoformat() if parsed else now_iso

        match_body = _COMMENT_BODY.search(block) or _FALLBACK_BODY.search(block)
        if not match_body:
            continue
        plain = _html_fragment_to_plain(match_body.group(1))
        if not plain:
            continue
        out.append((created_iso, plain))
    return out


def _write_dict_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    """
    댓글 행 목록을 UTF-8 BOM CSV로 기록한다.

    Args:
        path: 저장할 CSV 경로.
        fieldnames: CSV 헤더 순서.
        rows: 저장할 댓글 행 목록.
    """
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


######################
# DB 조회 및 수집 실행 관련
######################
def fetch_geek_crawling_rows(conn: psycopg.Connection, *, limit: int | None) -> list[tuple[Any, str, str]]:
    """
    crawling 테이블에서 GeekNews 게시글 목록을 조회한다.

    Args:
        conn: 활성화된 DB 연결 객체.
        limit: 조회할 최대 게시글 수.

    Returns:
        (crawling_id, article_url, thread) 튜플 목록.
    """
    with conn.cursor() as cur:
        if limit is not None:
            cur.execute(SQL_GEEK_ROWS + " LIMIT %s", (limit,))
        else:
            cur.execute(SQL_GEEK_ROWS)
        return [(row[0], row[1], row[2]) for row in cur.fetchall()]


def main() -> int:
    """
    DB의 GeekNews 게시글을 기준으로 댓글을 수집해 CSV로 저장한다.

    Returns:
        정상 종료 시 0, DB 연결 실패 시 1.
    """
    parser = argparse.ArgumentParser(description="GeekNews: DB crawling(geek_*)에서 article_url 읽어 댓글 CSV 저장")
    parser.add_argument("-o", "--output", type=Path, default=None, help="출력 CSV 경로")
    parser.add_argument("--timeout", type=float, default=45.0, help="HTTP 타임아웃(초)")
    parser.add_argument("--sleep-seconds", type=float, default=_DEFAULT_SLEEP_SECONDS, help="요청 사이 대기(초)")
    parser.add_argument("--limit-topics", type=int, default=None, help="처리할 crawling 행 수 상한")
    parser.add_argument("--max-comments", type=int, default=_MAX_COMMENTS_PER_TOPIC, help="토픽당 최대 댓글 수")
    args = parser.parse_args()

    date_sfx = datetime.now(_KST).strftime("%y%m%d")
    out_path = args.output or (Path(__file__).resolve().parent / f"comment_geeknews_{date_sfx}.csv")

    fieldnames = [
        "comment_id",
        "post_id",
        "user_id",
        "content",
        "created_at",
        "modify_at",
        "status_cd",
        "thread",
        "crawling_id",
    ]
    rows_out: list[dict[str, str]] = []

    try:
        conn = check_connection()
    except psycopg.Error:
        return 1

    try:
        topic_rows = fetch_geek_crawling_rows(conn, limit=args.limit_topics)
    finally:
        conn.close()

    # 게시글 단위로 순회하면서 각 토픽에서 댓글만 뽑아 누적한다.
    n_topics = len(topic_rows)
    for index, (crawling_id, article_url, thread) in enumerate(topic_rows):
        url = (article_url or "").strip()
        if not url:
            continue
        try:
            html = _fetch_text(url, args.timeout)
        except (TimeoutError, OSError, urllib.error.HTTPError, urllib.error.URLError) as exc:
            print(f"[skip] fetch 실패 crawling_id={crawling_id} url={url!r}: {exc}", file=sys.stderr)
            if index < n_topics - 1 and args.sleep_seconds > 0:
                time.sleep(args.sleep_seconds)
            continue
        except Exception as exc:
            print(f"[skip] fetch 오류 crawling_id={crawling_id}: {exc}", file=sys.stderr)
            if index < n_topics - 1 and args.sleep_seconds > 0:
                time.sleep(args.sleep_seconds)
            continue

        for created_iso, content in parse_comments_from_topic_html(html, max_comments=args.max_comments):
            rows_out.append(
                {
                    "comment_id": "",
                    "post_id": "",
                    "user_id": "",
                    "content": content,
                    "created_at": created_iso,
                    "modify_at": created_iso,
                    "status_cd": "",
                    "thread": thread or "",
                    "crawling_id": str(crawling_id) if crawling_id is not None else "",
                }
            )

        if index < n_topics - 1 and args.sleep_seconds > 0:
            time.sleep(args.sleep_seconds)

    _write_dict_csv(out_path, fieldnames, rows_out)
    print(f"저장: {out_path} ({len(rows_out)}행)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
