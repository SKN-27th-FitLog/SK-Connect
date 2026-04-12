'''
게시글 크롤링이 끝난 뒤 DB crawling 테이블에서 thread 가 geek_* 인 행만 골라 article_url 로 댓글을 수집한다.
행마다 thread·crawling_id 가 댓글 레코드에 붙는다. 토픽당 댓글은 최대 500개까지이며, 끝나면
comment_geeknews_YYMMDD.csv 로 저장한다(YYMMDD는 실행일).

CSV 컬럼
- comment_id, post_id: DB에 넣을 때 채울 예정이면 현재는 비움
- user_id: 익명·코드테이블 정책 확정 전까지 비움
- content: 댓글 본문
- created_at, modify_at: 페이지에 날짜가 있으면 그걸 쓰고, 없으면 수집 시각으로 맞춘다. modify_at 은 created_at 과 동일
- status_cd: 비움(추가 예정)
- thread, crawling_id: 소스 crawling 행과 매칭·조인용

댓글 추출은 GeekNews 토픽 HTML 기준으로 div.comment_row 블록을 순서대로 잘라
span.comment_contents 를 플레인 텍스트로 만든다. 작성일은 commentinfo 안의 comment?id= 링크 텍스트(YYYY-MM-DD)를 우선한다.
마크업이 바뀌면 코드 내 정규식과 함께 이 블록을 점검한다. SSR 로 내려온 댓글만 수집한다(페이지네이션·지연 로드는 미처리).
'''
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

# --- DB (insert_tables.py 와 동일한 환경 변수 규약) ---
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


_KST = ZoneInfo("Asia/Seoul")
_DEFAULT_USER_AGENT = "Mozilla/5.0 (compatible; it-threads-sample/1.0)"

# 댓글 행 시작: class=comment_row / "comment_row" / 'comment_row' 등 느슨하게 매칭
_COMMENT_ROW_OPEN = re.compile(
    r"<div\s+class\s*=\s*(?:\"comment_row\"|'comment_row'|comment_row)\b[^>]*>",
    re.IGNORECASE,
)
# 날짜: <a href='comment?id=123'>2024-10-15</a> 형태
_COMMENT_DATE = re.compile(
    r"href\s*=\s*[\"']comment\?id=\d+[\"']\s*>([^<]+)</a>",
    re.IGNORECASE,
)
# 본문: comment_contents 다음부터 commentreply 직전까지(닫는 span 매칭을 느슨하게)
_COMMENT_BODY = re.compile(
    r"comment_contents[^>]*>([\s\S]*?)</span>\s*</div>\s*<div\s+class\s*=\s*commentreply\b",
    re.IGNORECASE,
)
_FALLBACK_BODY = re.compile(r"comment_contents[^>]*>([\s\S]*?)</span>", re.IGNORECASE)

# 상한·sleep 기본값 (계획: 0.5~1.0초 권장 → 중간값)
_DEFAULT_SLEEP_SECONDS = 0.75
_MAX_COMMENTS_PER_TOPIC = 500

# thread 가 geek_ 로 시작하는 crawling 행만 가져온다(정규식 ^geek_).
SQL_GEEK_ROWS = """
SELECT crawling_id, article_url, thread
FROM crawling
WHERE thread ~ '^geek_'
  AND article_url IS NOT NULL
  AND trim(article_url) <> ''
ORDER BY crawling_id
"""


class _HTMLToText(HTMLParser):
    '''
    HTML 조각을 공백·줄바꿈 위주로 이어 붙인 플레인 텍스트로 만든다.
    gatter_content_geeknews 의 본문 변환과 같은 역할이다.
    '''

    _BLOCK = frozenset({"p", "div", "br", "hr", "li", "ul", "ol", "h1", "h2", "h3", "h4", "h5", "h6", "tr", "pre", "code"})

    def __init__(self) -> None:
        '''태그 사이 문자열을 누적할 버퍼를 초기화한다.'''
        super().__init__(convert_charrefs=True)
        self._parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        '''br·블록 태그 시작 시 줄바꿈 또는 공백을 넣어 경계를 맞춘다.'''
        t = tag.lower()
        if t == "br":
            self._parts.append("\n")
        elif t in self._BLOCK:
            self._parts.append(" ")

    def handle_endtag(self, tag: str) -> None:
        '''블록 태그 종료 시 공백을 넣어 단락 구분을 만든다.'''
        if tag.lower() in self._BLOCK:
            self._parts.append(" ")

    def handle_data(self, data: str) -> None:
        '''태그 사이의 문자 데이터를 그대로 누적한다.'''
        self._parts.append(data)

    def get_text(self) -> str:
        '''누적한 조각을 하나의 문자열로 이어 반환한다.'''
        return "".join(self._parts)


def _html_fragment_to_plain(fragment: str) -> str:
    '''HTML 조각을 파싱해 공백 정리된 플레인 텍스트로 만든다. 파싱 실패 시 빈 문자열.'''
    p = _HTMLToText()
    try:
        p.feed(fragment)
        p.close()
    except Exception:
        return ""
    text = p.get_text()
    return re.sub(r"\s+", " ", text).strip()


def _fetch_text(url: str, timeout: float, *, user_agent: str = _DEFAULT_USER_AGENT) -> str:
    '''GET 으로 URL 의 HTML 을 받아 UTF-8(오류 시 replace)로 디코드한 문자열을 반환한다.'''
    req = urllib.request.Request(url, headers={"User-Agent": user_agent})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", errors="replace")


def _parse_date_loose(s: str) -> datetime | None:
    '''댓글 링크 옆 날짜 문자열을 KST 기준 datetime 으로 파싱한다. 지원 형식이 아니면 None.'''
    s = s.strip()
    for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S"):
        try:
            dt = datetime.strptime(s, fmt)
            return dt.replace(tzinfo=_KST)
        except ValueError:
            continue
    return None


def iter_comment_row_blocks(html: str) -> list[str]:
    '''
    토픽 페이지 HTML 에서 div.comment_row 시작 위치마다 잘라 각 댓글 블록 문자열 목록을 만든다.
    문서 순서(댓글 나열 순)를 유지한다.
    '''
    starts = [m.start() for m in _COMMENT_ROW_OPEN.finditer(html)]
    blocks: list[str] = []
    for i, s in enumerate(starts):
        e = starts[i + 1] if i + 1 < len(starts) else len(html)
        blocks.append(html[s:e])
    return blocks


def parse_comments_from_topic_html(html: str, *, max_comments: int) -> list[tuple[str, str]]:
    '''
    토픽 HTML 에서 댓글을 추출한다.
    반환: (created_at ISO8601 문자열, 본문 플레인 텍스트) 튜플 리스트, 최대 max_comments 건.
    날짜를 못 찾으면 수집 시각(KST)을 쓴다. 본문·날짜 추출에 실패한 블록은 건너뛴다.
    '''
    out: list[tuple[str, str]] = []
    now_iso = datetime.now(_KST).isoformat()
    for block in iter_comment_row_blocks(html):
        if len(out) >= max_comments:
            break
        m_date = _COMMENT_DATE.search(block)
        date_s = m_date.group(1).strip() if m_date else ""
        dt = _parse_date_loose(date_s) if date_s else None
        created_iso = dt.isoformat() if dt else now_iso

        m_body = _COMMENT_BODY.search(block) or _FALLBACK_BODY.search(block)
        if not m_body:
            continue
        plain = _html_fragment_to_plain(m_body.group(1))
        if not plain:
            continue
        out.append((created_iso, plain))
    return out


def _write_dict_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    '''fieldnames 순으로 dict 행을 UTF-8 BOM CSV 로 기록한다(dict 에만 있는 키는 무시).'''
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


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


def main() -> int:
    '''
    CLI 진입점: DB 에서 geek_* 행을 읽어 각 article_url 의 댓글을 수집하고 CSV 로 저장한다.
    성공 시 0, DB 연결 실패 시 1 을 반환한다.
    '''
    p = argparse.ArgumentParser(description="GeekNews: DB crawling(geek_*)에서 article_url 읽어 댓글 CSV 저장")
    p.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="출력 CSV (기본: 이 폴더/comment_geeknews_YYMMDD.csv)",
    )
    p.add_argument("--timeout", type=float, default=45.0, help="HTTP 타임아웃(초)")
    p.add_argument(
        "--sleep-seconds",
        type=float,
        default=_DEFAULT_SLEEP_SECONDS,
        help=f"요청 사이 대기(초), 서버 부하 완화 (기본 {_DEFAULT_SLEEP_SECONDS})",
    )
    p.add_argument("--limit-topics", type=int, default=None, help="처리할 crawling 행 수 상한(앞쪽부터)")
    p.add_argument(
        "--max-comments",
        type=int,
        default=_MAX_COMMENTS_PER_TOPIC,
        help=f"토픽당 최대 댓글 수 (기본 {_MAX_COMMENTS_PER_TOPIC})",
    )
    args = p.parse_args()

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

        pairs = parse_comments_from_topic_html(html, max_comments=args.max_comments)
        for created_iso, content in pairs:
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

        if ti < n_topics - 1 and args.sleep_seconds > 0:
            time.sleep(args.sleep_seconds)

    _write_dict_csv(out_path, fieldnames, rows_out)
    print(f"저장: {out_path} ({len(rows_out)}행)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
