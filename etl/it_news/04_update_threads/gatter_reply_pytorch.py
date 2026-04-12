'''
DB crawling 에서 thread 가 pyto_* 인 행의 article_url(Discourse 토픽 URL)에 대해
토픽 JSON 의 답글(post_number > 1)을 수집해 comment_pytorch_YYMMDD.csv 로 저장한다.

한 번의 t/{id}.json 응답에 모든 글이 안 오면 post_stream.stream 과 posts 를 비교해
누락 post_id 를 t/{id}/posts.json?post_ids[]=... 로 추가 요청한다(배치 단위).

CSV 컬럼은 gatter_reply_geeknews.py 와 동일하다.
'''
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlsplit, urlunsplit
from zoneinfo import ZoneInfo

import psycopg

_DEFAULT_USER_AGENT = "Mozilla/5.0 (compatible; it-threads-sample/1.0)"
_KST = ZoneInfo("Asia/Seoul")
_DEFAULT_SLEEP_SECONDS = 0.75
_MAX_REPLIES_PER_TOPIC = 500
# posts.json 한 요청에 묶는 post_id 개수(URL 길이·서버 한도 고려)
_POST_IDS_CHUNK = 80


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


def topic_base_url(topic_url: str) -> str:
    '''토픽 URL 에서 scheme://host 만 반환한다.'''
    p = urlsplit(topic_url.strip())
    return f"{p.scheme}://{p.netloc}"


def _fetch_json(url: str, timeout: float, *, user_agent: str = _DEFAULT_USER_AGENT) -> Any:
    '''GET 응답을 UTF-8 로 읽어 json.loads 한 객체를 반환한다.'''
    req = urllib.request.Request(url, headers={"User-Agent": user_agent})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


class _HTMLToText(HTMLParser):
    '''Discourse post cooked HTML 조각을 플레인 텍스트로 변환한다.'''

    _BLOCK = frozenset({"p", "div", "br", "hr", "li", "ul", "ol", "h1", "h2", "h3", "h4", "h5", "h6", "tr", "pre", "td", "th", "code"})

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() == "br":
            self._parts.append("\n")
        elif tag.lower() in self._BLOCK:
            self._parts.append(" ")

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in self._BLOCK:
            self._parts.append(" ")

    def handle_data(self, data: str) -> None:
        self._parts.append(data)

    def get_text(self) -> str:
        return "".join(self._parts)


def _html_fragment_to_plain(fragment: str) -> str:
    '''HTML 조각을 플레인 텍스트로 만든다. 파싱 실패 시 빈 문자열.'''
    p = _HTMLToText()
    try:
        p.feed(fragment)
        p.close()
    except Exception:
        return ""
    return p.get_text()


def _iso_to_kst_iso(s: str | None, *, fallback: str) -> str:
    '''Discourse ISO8601 문자열(끝 Z 가능)을 KST 기준 ISO 문자열로 바꾼다. 실패 시 fallback.'''
    if not s or not isinstance(s, str):
        return fallback
    s = s.strip()
    try:
        if s.endswith("Z"):
            dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        else:
            dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=_KST)
        else:
            dt = dt.astimezone(_KST)
        return dt.isoformat()
    except ValueError:
        return fallback


def _merge_posts_by_id(*batches: list[dict[str, Any]]) -> dict[int, dict[str, Any]]:
    '''여러 응답의 posts 리스트를 id 기준으로 합친다.'''
    out: dict[int, dict[str, Any]] = {}
    for batch in batches:
        for p in batch:
            pid = p.get("id")
            if isinstance(pid, int):
                out[pid] = p
    return out


def fetch_all_topic_posts(topic_url: str, timeout: float) -> list[dict[str, Any]]:
    '''
    토픽 JSON 과 필요 시 posts.json 배치 호출로 해당 토픽의 모든 post 객체를 가져온다.
    post_number 순으로 정렬해 반환한다. 실패 시 예외를 던진다.
    '''
    jurl = topic_json_url(topic_url)
    data = _fetch_json(jurl, timeout)
    if not isinstance(data, dict):
        raise ValueError("토픽 JSON이 객체가 아님")
    topic_id = data.get("id")
    if not isinstance(topic_id, int):
        raise ValueError("토픽 JSON에 id 가 없음")

    ps = data.get("post_stream") or {}
    stream = ps.get("stream") or []
    if not isinstance(stream, list):
        stream = []
    first_posts = ps.get("posts") or []
    if not isinstance(first_posts, list):
        first_posts = []

    by_id = _merge_posts_by_id(first_posts)
    loaded = set(by_id.keys())
    missing = [pid for pid in stream if isinstance(pid, int) and pid not in loaded]

    base = topic_base_url(topic_url)
    while missing:
        chunk = missing[:_POST_IDS_CHUNK]
        missing = missing[_POST_IDS_CHUNK:]
        q = urllib.parse.urlencode([("post_ids[]", pid) for pid in chunk])
        posts_url = f"{base}/t/{topic_id}/posts.json?{q}"
        extra = _fetch_json(posts_url, timeout)
        eps = (extra.get("post_stream") or {}).get("posts") or []
        if isinstance(eps, list):
            by_id.update(_merge_posts_by_id(eps))

    ordered = sorted(by_id.values(), key=lambda p: int(p.get("post_number") or 0))
    return ordered


def iter_reply_rows_from_posts(
    posts: list[dict[str, Any]],
    *,
    max_replies: int,
    now_iso: str,
) -> list[tuple[str, str, str]]:
    '''
    post 목록에서 원글(post_number==1)을 제외한 답글만 (created_at, modify_at, content) 튜플로 낸다.
    최대 max_replies 건. 내용이 비면 해당 글은 건너뛴다.
    '''
    out: list[tuple[str, str, str]] = []
    for p in posts:
        if len(out) >= max_replies:
            break
        pn = p.get("post_number")
        if pn is None or int(pn) <= 1:
            continue
        if p.get("deleted_at"):
            continue
        cooked = p.get("cooked")
        if not cooked or not isinstance(cooked, str):
            continue
        plain = _html_fragment_to_plain(cooked)
        plain = re.sub(r"\s+", " ", plain).strip()
        if not plain:
            continue
        ca = _iso_to_kst_iso(p.get("created_at"), fallback=now_iso)
        ua = p.get("updated_at")
        if ua and isinstance(ua, str) and ua.strip():
            ma = _iso_to_kst_iso(ua, fallback=ca)
        else:
            ma = ca
        out.append((ca, ma, plain))
    return out


def _write_dict_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    '''fieldnames 순으로 dict 행을 UTF-8 BOM CSV 로 기록한다.'''
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def main() -> int:
    '''
    CLI: DB 에서 pyto_* 행을 읽어 Discourse 토픽 답글을 CSV 로 저장한다. 성공 0, DB 실패 1.
    '''
    p = argparse.ArgumentParser(description="PyTorchKR Discourse: crawling(pyto_*)에서 답글 CSV 저장")
    p.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="출력 CSV (기본: 이 폴더/comment_pytorch_YYMMDD.csv)",
    )
    p.add_argument("--timeout", type=float, default=45.0, help="HTTP 타임아웃(초)")
    p.add_argument(
        "--sleep-seconds",
        type=float,
        default=_DEFAULT_SLEEP_SECONDS,
        help=f"토픽 요청 사이 대기(초) (기본 {_DEFAULT_SLEEP_SECONDS})",
    )
    p.add_argument("--limit-topics", type=int, default=None, help="처리할 crawling 행 수 상한")
    p.add_argument(
        "--max-replies",
        type=int,
        default=_MAX_REPLIES_PER_TOPIC,
        help=f"토픽당 최대 답글 수 (기본 {_MAX_REPLIES_PER_TOPIC})",
    )
    args = p.parse_args()

    date_sfx = datetime.now(_KST).strftime("%y%m%d")
    out_path = args.output or (Path(__file__).resolve().parent / f"comment_pytorch_{date_sfx}.csv")

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
    now_iso = datetime.now(_KST).isoformat()

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
            posts = fetch_all_topic_posts(url, args.timeout)
            triples = iter_reply_rows_from_posts(posts, max_replies=args.max_replies, now_iso=now_iso)
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

        for ca, ma, content in triples:
            rows_out.append(
                {
                    "comment_id": "",
                    "post_id": "",
                    "user_id": "",
                    "content": content,
                    "created_at": ca,
                    "modify_at": ma,
                    "status_cd": "",
                    "thread": thread or "",
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
