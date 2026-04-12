"""
DB crawling 테이블에서 thread 가 geek_* 인 행의 article_url HTML을 받아,
토픽 본문(topic_contents) 안에 있는 이미지 URL을 수집한다. 이미지가 N개면 CSV에 N행.

본문 경계는 gatter_content_geeknews.extract_topic_body 와 동일 구간을 사용한다
(마크업 변경 시 gatter_content_geeknews.py 의 _TOPIC_OPEN / _RELATED_MARKER 와 함께 점검).

사용 예:
    python getter_images_geeknews.py
    python getter_images_geeknews.py --limit-topics 5 --sleep-seconds 1.0
"""
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
from pathlib import Path
from typing import Any
from urllib.parse import urljoin
from zoneinfo import ZoneInfo

import psycopg

# gatter_content_geeknews.py 와 동일(변경 시 양쪽 주석 유지)
_TOPIC_OPEN = "<div id='topic_contents'>"
_RELATED_MARKER = '<div class="related-topics">'

_DEFAULT_USER_AGENT = "Mozilla/5.0 (compatible; it-threads-sample/1.0)"
_KST = ZoneInfo("Asia/Seoul")
_DEFAULT_SLEEP_SECONDS = 0.75
_MAX_IMAGE_URL_LEN = 500

# img 태그 전체를 느슨하게 잡고 src / data-src 추출
_IMG_TAG = re.compile(r"<img\b[^>]*>", re.IGNORECASE | re.DOTALL)
_ATTR_SRC = re.compile(
    r"(?:src|data-src)\s*=\s*(?:\"([^\"]*)\"|'([^']*)'|([^\s>]+))",
    re.IGNORECASE,
)


def _env(name: str, default: str) -> str:
    '''환경 변수 name 을 읽고, 없거나 빈 문자열이면 default 를 반환한다.'''
    v = os.environ.get(name)
    return v if v is not None and v != "" else default


def get_connection_params() -> dict[str, Any]:
    '''psycopg.connect 에 넘길 호스트·포트·DB명·사용자·비밀번호 dict 를 환경 변수에서 만든다.'''
    return {
        "host": _env("PGHOST", "localhost"),
        "port": int(_env("PGPORT", "5432")),
        "dbname": _env("PGDATABASE", "service"),
        "user": _env("PGUSER", "user"),
        "password": _env("PGPASSWORD", "password"),
    }


def check_connection() -> psycopg.Connection:
    '''DB 에 연결해 SELECT 1 로 확인한 뒤 연결 객체를 반환한다. 실패 시 stderr 에 메시지를 남기고 예외를 다시 던진다.'''
    params = get_connection_params()
    try:
        conn = psycopg.connect(**params, connect_timeout=10)
        conn.execute("SELECT 1")
        return conn
    except psycopg.Error as e:
        print(f"DB 연결 실패: {e}", file=sys.stderr)
        raise


# thread 가 geek_ 로 시작하는 crawling 행만 가져온다(정규식 ^geek_).
SQL_GEEK_ROWS = """
SELECT crawling_id, article_url, thread
FROM crawling
WHERE thread ~ '^geek_'
  AND article_url IS NOT NULL
  AND trim(article_url) <> ''
ORDER BY crawling_id
"""


def fetch_geek_crawling_rows(conn: psycopg.Connection, *, limit: int | None) -> list[tuple[Any, str, str]]:
    '''
    crawling 에서 thread 가 geek_ 로 시작하는 행의 crawling_id, article_url, thread 를 조회한다.
    limit 가 있으면 SQL LIMIT 으로 앞에서부터 그 개수만 가져온다.
    반환: (crawling_id, article_url, thread) 튜플 리스트.
    '''
    with conn.cursor() as cur:
        if limit is not None:
            cur.execute(SQL_GEEK_ROWS + " LIMIT %s", (limit,))
        else:
            cur.execute(SQL_GEEK_ROWS)
        return [(r[0], r[1], r[2]) for r in cur.fetchall()]


def _fetch_text(url: str, timeout: float, *, user_agent: str = _DEFAULT_USER_AGENT) -> str:
    '''GET 으로 URL 의 HTML 을 받아 UTF-8(오류 시 replace)로 디코드한 문자열을 반환한다.'''
    req = urllib.request.Request(url, headers={"User-Agent": user_agent})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", errors="replace")


def extract_topic_contents_fragment(html: str) -> str | None:
    '''
    토픽 페이지 HTML 에서 div#topic_contents 직후부터 div.related-topics 직전까지의 HTML 조각을 반환한다.
    본문만 잘라 이미지 태그를 찾기 위한 구간이다. 경계를 찾지 못하면 None.
    '''
    start = html.find(_TOPIC_OPEN)
    if start == -1:
        return None
    start_content = start + len(_TOPIC_OPEN)
    end = html.find(_RELATED_MARKER, start_content)
    if end == -1:
        return None
    return html[start_content:end]


def _src_from_img_tag(tag: str) -> str | None:
    '''한 개의 <img ...> 태그 문자열에서 src 또는 data-src 속성 값을 꺼낸다. 없으면 None.'''
    m = _ATTR_SRC.search(tag)
    if not m:
        return None
    return (m.group(1) or m.group(2) or m.group(3) or "").strip() or None


def extract_image_urls_from_fragment(fragment: str, base_url: str) -> list[str]:
    '''
    본문 HTML 조각에서 <img> 를 순서대로 찾아 절대 URL 목록을 만든다.
    base_url은 상대 경로를 절대 URL 로 바꿀 때 쓴다. data: URL·길이 초과 URL·중복 URL은 제외한다.
    '''
    seen: set[str] = set()
    out: list[str] = []
    for m in _IMG_TAG.finditer(fragment):
        raw = _src_from_img_tag(m.group(0))
        if not raw or raw.lower().startswith("data:"):
            continue
        absolute = urljoin(base_url, raw).strip()
        if len(absolute) > _MAX_IMAGE_URL_LEN:
            continue
        if absolute in seen:
            continue
        seen.add(absolute)
        out.append(absolute)
    return out


def _write_dict_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    '''fieldnames 순으로 dict 행을 UTF-8 BOM CSV 로 기록한다(dict 에만 있는 키는 무시).'''
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def main() -> int:
    '''
    CLI 진입점: DB 에서 geek_* 행을 읽어 각 article_url 본문의 이미지 URL 을 수집하고 CSV 로 저장한다.
    이미지 하나당 한 행이다. 성공 시 0, DB 연결 실패 시 1 을 반환한다.
    '''
    p = argparse.ArgumentParser(description="GeekNews: 본문(topic_contents) 이미지 URL → CSV (이미지당 1행)")
    p.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="출력 CSV (기본: 이 폴더/images_geeknews_YYMMDD.csv)",
    )
    p.add_argument("--timeout", type=float, default=45.0)
    p.add_argument(
        "--sleep-seconds",
        type=float,
        default=_DEFAULT_SLEEP_SECONDS,
        help=f"요청 사이 대기(초) (기본 {_DEFAULT_SLEEP_SECONDS})",
    )
    p.add_argument("--limit-topics", type=int, default=None, help="처리할 crawling 행 수 상한")
    args = p.parse_args()

    date_sfx = datetime.now(_KST).strftime("%y%m%d")
    out_path = args.output or (Path(__file__).resolve().parent / f"images_geeknews_{date_sfx}.csv")
    fieldnames = ["image_id", "image_url", "thread", "article_url", "crawling_id"]

    rows_out: list[dict[str, str]] = []

    try:
        conn = check_connection()
    except psycopg.Error:
        return 1

    try:
        topic_rows = fetch_geek_crawling_rows(conn, limit=args.limit_topics)
    finally:
        conn.close()

    n_topics = len(topic_rows)
    for ti, (crawling_id, article_url, thread) in enumerate(topic_rows):
        url = (article_url or "").strip()
        if not url:
            continue
        try:
            html = _fetch_text(url, args.timeout)
        except (TimeoutError, OSError, urllib.error.HTTPError, urllib.error.URLError) as e:
            print(f"[skip] fetch 실패 crawling_id={crawling_id} url={url!r}: {e}", file=sys.stderr)
            if ti < n_topics - 1 and args.sleep_seconds > 0:
                time.sleep(args.sleep_seconds)
            continue
        except Exception as e:
            print(f"[skip] fetch 오류 crawling_id={crawling_id}: {e}", file=sys.stderr)
            if ti < n_topics - 1 and args.sleep_seconds > 0:
                time.sleep(args.sleep_seconds)
            continue

        frag = extract_topic_contents_fragment(html)
        if not frag:
            if ti < n_topics - 1 and args.sleep_seconds > 0:
                time.sleep(args.sleep_seconds)
            continue

        for img_url in extract_image_urls_from_fragment(frag, url):
            rows_out.append(
                {
                    "image_id": "",
                    "image_url": img_url,
                    "thread": thread or "",
                    "article_url": url,
                    "crawling_id": str(crawling_id) if crawling_id is not None else "",
                }
            )

        if ti < n_topics - 1 and args.sleep_seconds > 0:
            time.sleep(args.sleep_seconds)

    _write_dict_csv(out_path, fieldnames, rows_out)
    print(f"저장: {out_path} ({len(rows_out)}행)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
