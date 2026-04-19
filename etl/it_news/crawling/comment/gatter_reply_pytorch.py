"""
PyTorch 댓글 수집 스크립트.

이미 DB에 적재된 PyTorch 게시글을 기준으로 Discourse 댓글 JSON을 모으고,
원글을 제외한 reply만 comment raw CSV로 평탄화한다.
"""

from __future__ import annotations

import argparse
import csv
import json
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
from urllib.parse import urlsplit, urlunsplit
from zoneinfo import ZoneInfo

import psycopg

######################
# 스테이지 공통 설정 로딩 경로 보정 관련
######################
SCRIPT_STAGE_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_STAGE_ROOT) not in sys.path:
    sys.path.append(str(SCRIPT_STAGE_ROOT))

from common.settings import env, get_config

######################
# 설정 기반 상수 및 쿼리 관련
######################
CONFIG = get_config()
SOURCE_CONFIG = CONFIG["sources"]["pytorch"]["comment"]
CSV_ENCODING = CONFIG["paths"]["csv_encoding"]
_DEFAULT_USER_AGENT = SOURCE_CONFIG["user_agent"]
_KST = ZoneInfo(CONFIG["timezone"])
_DEFAULT_SLEEP_SECONDS = SOURCE_CONFIG["sleep_seconds"]
_MAX_REPLIES_PER_TOPIC = SOURCE_CONFIG["max_replies"]
_POST_IDS_CHUNK = SOURCE_CONFIG["post_ids_chunk"]


######################
# DB 연결 정보 구성 관련
######################
def get_connection_params() -> dict[str, Any]:
    """
    psycopg 연결 인자를 환경 변수 기준으로 조립한다.

    Returns:
        PostgreSQL 연결 파라미터 딕셔너리.
    """
    # DB 연결값은 스테이지 `.env`에서 읽고, 코드에는 fallback만 남긴다.
    return {
        "host": env("PGHOST", "localhost"),
        "port": int(env("PGPORT", "5432")),
        "dbname": env("PGDATABASE", "service"),
        "user": env("PGUSER", "user"),
        "password": env("PGPASSWORD", "password"),
    }


def check_connection() -> psycopg.Connection:
    """
    DB 연결 가능 여부를 확인한 뒤 연결 객체를 반환한다.

    Returns:
        사용 가능한 psycopg 연결 객체.
    """
    params = get_connection_params()
    try:
        conn = psycopg.connect(**params, connect_timeout=SOURCE_CONFIG["connect_timeout"])
        conn.execute("SELECT 1")
        return conn
    except psycopg.Error as exc:
        print(f"DB 연결 실패: {exc}", file=sys.stderr)
        raise


SQL_PYTORCH_ROWS = f"""
SELECT crawling_id, article_url, thread
FROM crawling
WHERE thread ~ '{SOURCE_CONFIG["thread_pattern"]}'
  AND article_url IS NOT NULL
  AND trim(article_url) <> ''
ORDER BY crawling_id
"""


######################
# DB 대상 게시글 조회 및 URL 변환 관련
######################
def fetch_pytorch_crawling_rows(conn: psycopg.Connection, *, limit: int | None) -> list[tuple[Any, str, str]]:
    """
    crawling 테이블에서 PyTorch 게시글 목록을 조회한다.

    Args:
        conn: 활성화된 DB 연결 객체.
        limit: 조회할 최대 게시글 수.

    Returns:
        (crawling_id, article_url, thread) 튜플 목록.
    """
    # comment crawling의 부모 집합은 crawling 테이블의 PyTorch 게시글 목록이다.
    with conn.cursor() as cur:
        if limit is not None:
            cur.execute(SQL_PYTORCH_ROWS + " LIMIT %s", (limit,))
        else:
            cur.execute(SQL_PYTORCH_ROWS)
        return [(row[0], row[1], row[2]) for row in cur.fetchall()]


def topic_json_url(topic_url: str) -> str:
    """
    Discourse 토픽 URL을 같은 리소스의 JSON URL로 바꾼다.

    Args:
        topic_url: 브라우저용 토픽 URL.

    Returns:
        `.json` 확장자가 붙은 API URL.
    """
    parts = urlsplit(topic_url.strip())
    path = parts.path or ""
    if path.endswith(".json"):
        return topic_url.strip()
    path = path.rstrip("/") + ".json"
    return urlunsplit((parts.scheme, parts.netloc, path, parts.query, parts.fragment))


def topic_base_url(topic_url: str) -> str:
    """
    Discourse 토픽 URL에서 scheme://host 부분만 추출한다.

    Args:
        topic_url: 토픽 URL.

    Returns:
        호스트 기준 URL.
    """
    parts = urlsplit(topic_url.strip())
    return f"{parts.scheme}://{parts.netloc}"


def _fetch_json(url: str, timeout: float, *, user_agent: str = _DEFAULT_USER_AGENT) -> Any:
    """
    Discourse JSON 응답을 받아 파이썬 객체로 변환한다.

    Args:
        url: 가져올 JSON URL.
        timeout: HTTP 타임아웃(초).
        user_agent: 요청 시 사용할 User-Agent.

    Returns:
        JSON 디코드 결과 객체.
    """
    req = urllib.request.Request(url, headers={"User-Agent": user_agent})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode())


######################
# HTML → 텍스트 및 댓글 변환 관련
######################
class _HTMLToText(HTMLParser):
    """Discourse cooked HTML을 사람이 읽는 평문으로 바꾸기 위한 간단한 파서."""

    _BLOCK = frozenset({"p", "div", "br", "hr", "li", "ul", "ol", "h1", "h2", "h3", "h4", "h5", "h6", "tr", "pre", "td", "th", "code"})

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
    Discourse 댓글 HTML 조각을 평문으로 변환한다.

    Args:
        fragment: cooked HTML 조각.

    Returns:
        평문 문자열. 파싱 실패 시 빈 문자열.
    """
    parser = _HTMLToText()
    try:
        parser.feed(fragment)
        parser.close()
    except Exception:
        return ""
    return parser.get_text()


def _iso_to_kst_iso(value: str | None, *, fallback: str) -> str:
    """
    Discourse ISO 시각 문자열을 KST ISO 문자열로 정규화한다.

    Args:
        value: 원본 ISO 시각 문자열.
        fallback: 파싱 실패 시 사용할 기본 ISO 문자열.

    Returns:
        KST 기준 ISO 문자열.
    """
    if not value or not isinstance(value, str):
        return fallback
    text = value.strip()
    try:
        if text.endswith("Z"):
            dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
        else:
            dt = datetime.fromisoformat(text)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=_KST)
        else:
            dt = dt.astimezone(_KST)
        return dt.isoformat()
    except ValueError:
        return fallback


def _merge_posts_by_id(*batches: list[dict[str, Any]]) -> dict[int, dict[str, Any]]:
    """
    여러 JSON 응답의 posts 배열을 post ID 기준으로 합친다.

    Args:
        *batches: 병합할 post 딕셔너리 목록들.

    Returns:
        post ID를 키로 하는 병합 결과 딕셔너리.
    """
    out: dict[int, dict[str, Any]] = {}
    for batch in batches:
        for post in batch:
            post_id = post.get("id")
            if isinstance(post_id, int):
                out[post_id] = post
    return out


######################
# Discourse 토픽 전체 답글 수집 관련
######################
def fetch_all_topic_posts(topic_url: str, timeout: float) -> list[dict[str, Any]]:
    """
    토픽 JSON과 추가 posts.json 호출을 합쳐 전체 post 목록을 가져온다.

    Args:
        topic_url: Discourse 토픽 URL.
        timeout: HTTP 타임아웃(초).

    Returns:
        post_number 순으로 정렬된 post 딕셔너리 목록.
    """
    data = _fetch_json(topic_json_url(topic_url), timeout)
    if not isinstance(data, dict):
        raise ValueError("토픽 JSON이 객체가 아님")
    topic_id = data.get("id")
    if not isinstance(topic_id, int):
        raise ValueError("토픽 JSON에 id 가 없음")

    post_stream = data.get("post_stream") or {}
    stream = post_stream.get("stream") or []
    if not isinstance(stream, list):
        stream = []
    first_posts = post_stream.get("posts") or []
    if not isinstance(first_posts, list):
        first_posts = []

    by_id = _merge_posts_by_id(first_posts)
    missing = [post_id for post_id in stream if isinstance(post_id, int) and post_id not in by_id]

    base = topic_base_url(topic_url)
    # 첫 응답에 안 담긴 post_id만 추가 요청해서 긴 스레드도 누락 없이 모은다.
    while missing:
        chunk = missing[:_POST_IDS_CHUNK]
        missing = missing[_POST_IDS_CHUNK:]
        query = urllib.parse.urlencode([("post_ids[]", post_id) for post_id in chunk])
        extra = _fetch_json(f"{base}/t/{topic_id}/posts.json?{query}", timeout)
        extra_posts = (extra.get("post_stream") or {}).get("posts") or []
        if isinstance(extra_posts, list):
            by_id.update(_merge_posts_by_id(extra_posts))

    return sorted(by_id.values(), key=lambda post: int(post.get("post_number") or 0))


def iter_reply_rows_from_posts(posts: list[dict[str, Any]], *, max_replies: int, now_iso: str) -> list[tuple[str, str, str]]:
    """
    post 목록에서 원글을 제외한 댓글 행만 추출한다.

    Args:
        posts: Discourse post 딕셔너리 목록.
        max_replies: 토픽당 최대 댓글 수.
        now_iso: 시각 파싱 실패 시 사용할 기본 ISO 문자열.

    Returns:
        (created_at, modify_at, content) 튜플 목록.
    """
    out: list[tuple[str, str, str]] = []
    for post in posts:
        if len(out) >= max_replies:
            break
        post_number = post.get("post_number")
        if post_number is None or int(post_number) <= 1:
            continue
        if post.get("deleted_at"):
            continue
        cooked = post.get("cooked")
        if not cooked or not isinstance(cooked, str):
            continue
        plain = re.sub(r"\s+", " ", _html_fragment_to_plain(cooked)).strip()
        if not plain:
            continue
        created_at = _iso_to_kst_iso(post.get("created_at"), fallback=now_iso)
        updated_at = post.get("updated_at")
        modify_at = _iso_to_kst_iso(updated_at, fallback=created_at) if updated_at else created_at
        out.append((created_at, modify_at, plain))
    return out


def _write_dict_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    """
    댓글 행 목록을 UTF-8 BOM CSV로 기록한다.

    Args:
        path: 저장할 CSV 경로.
        fieldnames: CSV 헤더 순서.
        rows: 저장할 댓글 행 목록.
    """
    with path.open("w", encoding=CSV_ENCODING, newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


######################
# comment crawling 실행 흐름 관련
######################
def main() -> int:
    """
    DB의 PyTorch 게시글을 기준으로 답글을 수집해 CSV로 저장한다.

    Returns:
        정상 종료 시 0, DB 연결 실패 시 1.
    """
    parser = argparse.ArgumentParser(description="PyTorchKR Discourse: crawling(pyto_*)에서 답글 CSV 저장")
    parser.add_argument("-o", "--output", type=Path, default=None, help="출력 CSV 경로")
    parser.add_argument("--timeout", type=float, default=SOURCE_CONFIG["timeout"], help="HTTP 타임아웃(초)")
    parser.add_argument("--sleep-seconds", type=float, default=_DEFAULT_SLEEP_SECONDS, help="토픽 요청 사이 대기(초)")
    parser.add_argument("--limit-topics", type=int, default=None, help="처리할 crawling 행 수 상한")
    parser.add_argument("--max-replies", type=int, default=_MAX_REPLIES_PER_TOPIC, help="토픽당 최대 답글 수")
    args = parser.parse_args()

    date_sfx = datetime.now(_KST).strftime("%y%m%d")
    out_path = args.output or (Path(__file__).resolve().parent / f"{SOURCE_CONFIG['default_output_prefix']}{date_sfx}.csv")

    # 이 컬럼 집합을 기준으로 comment cleaning/save가 동일한 입력 스키마를 사용한다.
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

    # 게시글 단위로 순회하면서 토픽의 모든 답글을 평탄화해 누적한다.
    n_topics = len(topic_rows)
    for index, (crawling_id, article_url, thread) in enumerate(topic_rows):
        url = (article_url or "").strip()
        if not url:
            continue
        try:
            posts = fetch_all_topic_posts(url, args.timeout)
            triples = iter_reply_rows_from_posts(posts, max_replies=args.max_replies, now_iso=now_iso)
        except (TimeoutError, OSError, urllib.error.HTTPError, urllib.error.URLError) as exc:
            print(f"[skip] fetch 실패 crawling_id={crawling_id} url={url!r}: {exc}", file=sys.stderr)
            if index < n_topics - 1 and args.sleep_seconds > 0:
                time.sleep(args.sleep_seconds)
            continue
        except json.JSONDecodeError as exc:
            print(f"[skip] JSON 실패 crawling_id={crawling_id}: {exc}", file=sys.stderr)
            if index < n_topics - 1 and args.sleep_seconds > 0:
                time.sleep(args.sleep_seconds)
            continue
        except Exception as exc:
            print(f"[skip] 처리 오류 crawling_id={crawling_id}: {exc}", file=sys.stderr)
            if index < n_topics - 1 and args.sleep_seconds > 0:
                time.sleep(args.sleep_seconds)
            continue

        for created_at, modify_at, content in triples:
            rows_out.append(
                {
                    "comment_id": "",
                    "post_id": "",
                    "user_id": "",
                    "content": content,
                    "created_at": created_at,
                    "modify_at": modify_at,
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
