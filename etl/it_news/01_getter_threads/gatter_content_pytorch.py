"""
PyTorchKR(Discourse) 토픽 CSV에 state / content 컬럼을 채운다.
각 행의 topic_url에 대응하는 토픽 JSON(.json)에서 원글(post_number=1)의 cooked HTML을 플레인 텍스트로 저장.
기본적으로 content는 Excel·뷰어 안정을 위해 앞에서부터 최대 4000자로 자른다(--max-content-chars).

사용 예:
    python gatter_content_pytorch.py -i thread_pytorch.csv
    python gatter_content_pytorch.py -i thread_pytorch.csv -o out.csv --limit 3 --timeout 45
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import time
import urllib.error
import urllib.request
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

_DEFAULT_USER_AGENT = "Mozilla/5.0 (compatible; it--sample/1.0)"


def _fetch_json(url: str, timeout: float, *, user_agent: str = _DEFAULT_USER_AGENT) -> Any:
    '''GET 응답을 UTF-8로 읽어 json.loads한 파이썬 객체를 반환한다.'''
    req = urllib.request.Request(url, headers={"User-Agent": user_agent})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def topic_json_url(topic_url: str) -> str:
    """Discourse 토픽 페이지 URL → 동일 리소스의 .json URL."""
    parts = urlsplit(topic_url.strip())
    path = parts.path or ""
    if path.endswith(".json"):
        return topic_url.strip()
    path = path.rstrip("/") + ".json"
    return urlunsplit((parts.scheme, parts.netloc, path, parts.query, parts.fragment))


class _HTMLToText(HTMLParser):
    """cooked HTML 조각을 공백 위주로 이어 붙인 플레인 텍스트로 변환."""

    _BLOCK = frozenset({"p", "div", "br", "hr", "li", "ul", "ol", "h1", "h2", "h3", "h4", "h5", "h6", "tr", "pre", "td", "th"})

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        '''블록 태그·br 시작 시 줄바꿈·공백을 넣어 텍스트 경계를 맞춘다.'''
        if tag.lower() == "br":
            self._parts.append("\n")
        elif tag.lower() in self._BLOCK:
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
    '''HTML 조각을 _HTMLToText로 파싱해 공백 정리된 플레인 텍스트로 만든다. 파싱 실패 시 빈 문자열.'''
    p = _HTMLToText()
    try:
        p.feed(fragment)
        p.close()
    except Exception:
        return ""
    return p.get_text()


def extract_first_post_plain(data: dict[str, Any]) -> str | None:
    """토픽 JSON dict에서 원글 cooked → 플레인 텍스트. 실패 시 None."""
    posts = (data.get("post_stream") or {}).get("posts") or []
    op = next((p for p in posts if p.get("post_number") == 1), None)
    if op is None and posts:
        op = posts[0]
    if not op:
        return None
    cooked = op.get("cooked")
    if not cooked or not isinstance(cooked, str):
        return None
    plain = _html_fragment_to_plain(cooked)
    plain = re.sub(r"\s+", " ", plain).strip()
    return plain if plain else None


def _write_dict_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    '''fieldnames 순으로 dict 행을 UTF-8 BOM CSV로 기록한다(extrasaction=ignore).'''
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def _merge_fieldnames(existing: list[str]) -> list[str]:
    '''기존 헤더 뒤에 state·content 열이 없으면 순서대로 추가한 목록을 반환한다.'''
    out = list(existing)
    for col in ("state", "content"):
        if col not in out:
            out.append(col)
    return out


_ELLIPSIS = "…"


def _truncate_text(s: str, max_chars: int) -> str:
    """max_chars <= 0 이면 잘라내지 않음. 그 외 Unicode 코드포인트 기준 앞쪽만 유지하고 … 접미."""
    if max_chars <= 0 or len(s) <= max_chars:
        return s
    suf = _ELLIPSIS
    n = len(suf)
    if max_chars <= n:
        return s[:max_chars]
    return s[: max_chars - n] + suf


def enrich_rows(
    rows: list[dict[str, str]],
    *,
    timeout: float,
    delay: float,
    limit: int | None,
    max_content_chars: int,
) -> list[dict[str, str]]:
    """각 행에 state, content 설정. 예외는 행 단위로 삼키고 fail 처리."""
    n_fetch = len(rows) if limit is None else min(limit, len(rows))
    out: list[dict[str, str]] = []
    for i, row in enumerate(rows):
        if i >= n_fetch:
            out.append(dict(row))
            continue

        url = (row.get("topic_url") or "").strip()
        if not url:
            out.append({**row, "state": "fail", "content": ""})
        else:
            text: str | None = None
            try:
                jurl = topic_json_url(url)
                data = _fetch_json(jurl, timeout)
                if isinstance(data, dict):
                    text = extract_first_post_plain(data)
            except TimeoutError:
                text = None
            except OSError:
                text = None
            except urllib.error.HTTPError:
                text = None
            except urllib.error.URLError:
                text = None
            except json.JSONDecodeError:
                text = None
            except Exception:
                text = None

            if text:
                out.append(
                    {**row, "state": "ok", "content": _truncate_text(text, max_content_chars)},
                )
            else:
                out.append({**row, "state": "fail", "content": ""})

        if delay > 0 and i < n_fetch - 1:
            time.sleep(delay)

    return out


def main() -> int:
    '''CLI: 입력 CSV를 읽어 topic_url의 Discourse JSON 원글 본문을 채운 뒤 _with_content CSV로 저장한다.'''
    p = argparse.ArgumentParser(
        description="PyTorchKR Discourse CSV: topic_url 토픽 JSON에서 원글 본문 → state(ok/fail), content",
    )
    default_dir = Path(__file__).resolve().parent
    p.add_argument(
        "-i",
        "--input",
        type=Path,
        default=default_dir / "thread_pytorch.csv",
        help="입력 CSV (기본: 이 폴더/thread_pytorch.csv)",
    )
    p.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="출력 CSV (기본: 입력과 같은 폴더에 <이름>_with_content.csv)",
    )
    p.add_argument("--timeout", type=float, default=30.0, help="행당 HTTP 타임아웃(초)")
    p.add_argument("--delay", type=float, default=0.0, help="행 사이 대기(초), 서버 부하 완화용")
    p.add_argument("--limit", type=int, default=None, help="본문 수집할 최대 행 수(앞에서부터); 나머지 행은 그대로 출력")
    p.add_argument(
        "--max-content-chars",
        type=int,
        default=4000,
        help="content 최대 글자 수(Unicode 기준). Excel/뷰어 안정용. 0=무제한",
    )
    args = p.parse_args()

    inp: Path = args.input
    if not inp.is_file():
        print(f"입력 파일 없음: {inp}", file=sys.stderr)
        return 1

    out_path: Path = args.output or inp.with_name(f"{inp.stem}_with_content{inp.suffix}")

    with inp.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            print("CSV 헤더가 없습니다.", file=sys.stderr)
            return 1
        fieldnames = _merge_fieldnames(list(reader.fieldnames))
        rows = list(reader)

    for r in rows:
        r.setdefault("state", "")
        r.setdefault("content", "")

    enriched = enrich_rows(
        rows,
        timeout=args.timeout,
        delay=args.delay,
        limit=args.limit,
        max_content_chars=args.max_content_chars,
    )

    _write_dict_csv(out_path, fieldnames, enriched)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
