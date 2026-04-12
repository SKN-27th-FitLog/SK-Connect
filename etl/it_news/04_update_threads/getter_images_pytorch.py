"""
DB crawling 에서 thread 가 pyto_* 인 행의 article_url 에 대해 Discourse 토픽 JSON 의
원글(post_number==1) cooked HTML 안의 이미지 URL 을 수집한다. 이미지가 N 개면 CSV 에 N 행.

getter_images_geeknews.py 와 동일한 CSV 컬럼·중복·길이 정책을 쓴다(본문만 Discourse cooked).
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlsplit, urlunsplit
from zoneinfo import ZoneInfo

import psycopg

_DEFAULT_USER_AGENT = "Mozilla/5.0 (compatible; it-threads-sample/1.0)"
_KST = ZoneInfo("Asia/Seoul")
_DEFAULT_SLEEP_SECONDS = 0.75
_MAX_IMAGE_URL_LEN = 500

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


SQL_PYTORCH_ROWS = """
SELECT crawling_id, article_url, thread
FROM crawling
WHERE thread ~ '^pyto_'
  AND article_url IS NOT NULL
  AND trim(article_url) <> ''
ORDER BY crawling_id
"""


def fetch_pytorch_crawling_rows(conn: psycopg.Connection, *, limit: int | None) -> list[tuple[Any, str, str]]:
    '''
    crawling 에서 thread 가 pyto_ 로 시작하는 행의 crawling_id, article_url, thread 를 조회한다.
    limit 가 있으면 SQL LIMIT 으로 앞에서부터 그 개수만 가져온다.
    '''
    with conn.cursor() as cur:
        if limit is not None:
            cur.execute(SQL_PYTORCH_ROWS + " LIMIT %s", (limit,))
        else:
            cur.execute(SQL_PYTORCH_ROWS)
        return [(r[0], r[1], r[2]) for r in cur.fetchall()]


def topic_json_url(topic_url: str) -> str:
    '''Discourse 토픽 페이지 URL → 동일 리소스의 .json URL.'''
    parts = urlsplit(topic_url.strip())
    path = parts.path or ""
    if path.endswith(".json"):
        return topic_url.strip()
    path = path.rstrip("/") + ".json"
    return urlunsplit((parts.scheme, parts.netloc, path, parts.query, parts.fragment))


def _fetch_json(url: str, timeout: float, *, user_agent: str = _DEFAULT_USER_AGENT) -> Any:
    '''GET 응답을 UTF-8 로 읽어 json.loads 한 객체를 반환한다.'''
    req = urllib.request.Request(url, headers={"User-Agent": user_agent})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def extract_first_post_cooked(data: dict[str, Any]) -> str | None:
    '''토픽 JSON 에서 원글(post_number==1) 의 cooked HTML 문자열. 없으면 None.'''
    posts = (data.get("post_stream") or {}).get("posts") or []
    op = next((p for p in posts if p.get("post_number") == 1), None)
    if op is None and posts:
        op = posts[0]
    if not op:
        return None
    cooked = op.get("cooked")
    return cooked if isinstance(cooked, str) and cooked.strip() else None


def _src_from_img_tag(tag: str) -> str | None:
    '''한 개의 <img ...> 태그 문자열에서 src 또는 data-src 속성 값을 꺼낸다. 없으면 None.'''
    m = _ATTR_SRC.search(tag)
    if not m:
        return None
    return (m.group(1) or m.group(2) or m.group(3) or "").strip() or None


def extract_image_urls_from_cooked(cooked: str, base_url: str) -> list[str]:
    '''
    cooked HTML 에서 <img> 를 순서대로 찾아 절대 URL 목록을 만든다.
    base_url 은 상대 경로를 절대 URL 로 바꿀 때 쓴다. data:·길이 초과·토픽 내 중복은 제외한다.
    '''
    seen: set[str] = set()
    out: list[str] = []
    for m in _IMG_TAG.finditer(cooked):
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
    '''fieldnames 순으로 dict 행을 UTF-8 BOM CSV 로 기록한다.'''
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def main() -> int:
    '''
    CLI: DB 에서 pyto_* 행을 읽어 원글 본문 이미지 URL 을 CSV 로 저장한다. 성공 0, DB 실패 1.
    '''
    p = argparse.ArgumentParser(description="PyTorchKR Discourse: 원글 cooked 이미지 URL → CSV (이미지당 1행)")
    p.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="출력 CSV (기본: 이 폴더/images_pytorch_YYMMDD.csv)",
    )
    p.add_argument("--timeout", type=float, default=45.0)
    p.add_argument(
        "--sleep-seconds",
        type=float,
        default=_DEFAULT_SLEEP_SECONDS,
        help=f"토픽 요청 사이 대기(초) (기본 {_DEFAULT_SLEEP_SECONDS})",
    )
    p.add_argument("--limit-topics", type=int, default=None, help="처리할 crawling 행 수 상한")
    args = p.parse_args()

    date_sfx = datetime.now(_KST).strftime("%y%m%d")
    out_path = args.output or (Path(__file__).resolve().parent / f"images_pytorch_{date_sfx}.csv")
    fieldnames = ["image_id", "image_url", "thread", "article_url", "crawling_id"]

    rows_out: list[dict[str, str]] = []

    try:
        conn = check_connection()
    except psycopg.Error:
        return 1

    try:
        topic_rows = fetch_pytorch_crawling_rows(conn, limit=args.limit_topics)
    finally:
        conn.close()

    n_topics = len(topic_rows)
    for ti, (crawling_id, article_url, thread) in enumerate(topic_rows):
        url = (article_url or "").strip()
        if not url:
            continue
        try:
            jurl = topic_json_url(url)
            data = _fetch_json(jurl, args.timeout)
            if not isinstance(data, dict):
                raise ValueError("토픽 JSON이 객체가 아님")
            cooked = extract_first_post_cooked(data)
        except (TimeoutError, OSError, urllib.error.HTTPError, urllib.error.URLError) as e:
            print(f"[skip] fetch 실패 crawling_id={crawling_id} url={url!r}: {e}", file=sys.stderr)
            if ti < n_topics - 1 and args.sleep_seconds > 0:
                time.sleep(args.sleep_seconds)
            continue
        except json.JSONDecodeError as e:
            print(f"[skip] JSON 실패 crawling_id={crawling_id}: {e}", file=sys.stderr)
            if ti < n_topics - 1 and args.sleep_seconds > 0:
                time.sleep(args.sleep_seconds)
            continue
        except Exception as e:
            print(f"[skip] 처리 오류 crawling_id={crawling_id}: {e}", file=sys.stderr)
            if ti < n_topics - 1 and args.sleep_seconds > 0:
                time.sleep(args.sleep_seconds)
            continue

        if not cooked:
            if ti < n_topics - 1 and args.sleep_seconds > 0:
                time.sleep(args.sleep_seconds)
            continue

        for img_url in extract_image_urls_from_cooked(cooked, url):
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
