"""
GeekNews 토픽 CSV에 state / content 컬럼을 채운다.
각 행의 article_url HTML에서 <div id='topic_contents'> 본문을 추출해 플레인 텍스트로 저장.
기본적으로 content는 Excel·뷰어 안정을 위해 앞에서부터 최대 4000자로 자른다(--max-content-chars).
"""
from __future__ import annotations

import argparse
import csv
import logging
import re
import sys
import time
import urllib.error
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

######################
# 스테이지 공통 설정 로딩 경로 보정 관련
######################
SCRIPT_STAGE_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_STAGE_ROOT) not in sys.path:
    sys.path.append(str(SCRIPT_STAGE_ROOT))

from common.settings import get_config

######################
# 설정 기반 상수 관련
######################
CONFIG = get_config()
CONTENT_CONFIG = CONFIG["sources"]["geeknews"]["content"]
CSV_ENCODING = CONFIG["paths"]["csv_encoding"]
_DEFAULT_USER_AGENT = CONTENT_CONFIG["user_agent"]
logger = logging.getLogger(__name__)

_TOPIC_OPEN = "<div id='topic_contents'>"
_RELATED_MARKER = '<div class="related-topics">'


######################
# HTTP 및 HTML → 텍스트 변환 관련
######################
def _fetch_text(url: str, timeout: float, *, user_agent: str = _DEFAULT_USER_AGENT) -> str:
    """
    토픽 페이지 HTML을 가져온다.

    Args:
        url: 가져올 페이지 URL.
        timeout: HTTP 타임아웃(초).
        user_agent: 요청 시 사용할 User-Agent.

    Returns:
        UTF-8 문자열로 디코드된 HTML 본문.
    """
    req = urllib.request.Request(url, headers={"User-Agent": user_agent})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", errors="replace")


class _HTMLToText(HTMLParser):
    """GeekNews 본문 HTML 조각을 평문으로 바꾸기 위한 간단한 파서."""

    _BLOCK = frozenset({"p", "div", "br", "hr", "li", "ul", "ol", "h1", "h2", "h3", "h4", "h5", "h6", "tr", "pre"})

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
    본문 HTML 조각을 평문 문자열로 변환한다.

    Args:
        fragment: 본문 HTML 조각.

    Returns:
        평문 문자열. 파싱 실패 시 빈 문자열.
    """
    p = _HTMLToText()
    try:
        p.feed(fragment)
        p.close()
    except Exception:
        return ""
    return p.get_text()


######################
# 본문 추출 및 CSV 갱신 관련
######################
def extract_topic_body(html: str) -> str | None:
    """
    토픽 HTML에서 본문 영역만 잘라 평문으로 반환한다.

    Args:
        html: 토픽 페이지 HTML 문자열.

    Returns:
        본문 평문 문자열 또는 추출 실패 시 None.
    """
    start = html.find(_TOPIC_OPEN)
    if start == -1:
        return None
    start_content = start + len(_TOPIC_OPEN)
    end = html.find(_RELATED_MARKER, start_content)
    if end == -1:
        return None
    fragment = html[start_content:end]
    fragment = re.sub(r"(?:\s*</div>)+$", "", fragment, flags=re.IGNORECASE)
    plain = _html_fragment_to_plain(fragment)
    plain = re.sub(r"\s+", " ", plain).strip()
    return plain if plain else None


def _write_dict_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    """
    행 목록을 UTF-8 BOM CSV로 기록한다.

    Args:
        path: 저장할 CSV 경로.
        fieldnames: CSV 헤더 순서.
        rows: 저장할 행 목록.
    """
    with path.open("w", encoding=CSV_ENCODING, newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def _merge_fieldnames(existing: list[str]) -> list[str]:
    """
    원본 CSV 헤더에 `state`, `content` 컬럼이 없으면 뒤에 추가한다.

    Args:
        existing: 기존 헤더 목록.

    Returns:
        필요한 컬럼이 보강된 헤더 목록.
    """
    # 원본 컬럼 순서를 유지한 채 결과 컬럼만 뒤에 덧붙인다.
    out = list(existing)
    for col in ("state", "content"):
        if col not in out:
            out.append(col)
    return out


_ELLIPSIS = CONTENT_CONFIG["ellipsis"]


def _truncate_text(s: str, max_chars: int) -> str:
    """
    본문 길이를 최대 글자 수 기준으로 자른다.

    Args:
        s: 원본 문자열.
        max_chars: 허용할 최대 글자 수.

    Returns:
        길이 제한이 적용된 문자열.
    """
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
    """
    입력 CSV 각 행에 본문 수집 결과를 반영해 `state`, `content`를 채운다.

    Args:
        rows: 원본 CSV 행 목록.
        timeout: 행당 HTTP 타임아웃(초).
        delay: 행 사이 대기 시간.
        limit: 본문 수집을 시도할 최대 행 수.
        max_content_chars: 본문 최대 글자 수.

    Returns:
        본문 수집 결과가 반영된 행 목록.
    """
    n_fetch = len(rows) if limit is None else min(limit, len(rows))
    out: list[dict[str, str]] = []
    for i, row in enumerate(rows):
        if i >= n_fetch:
            out.append(dict(row))
            continue

        url = (row.get("article_url") or "").strip()
        if not url:
            out.append({**row, "state": "fail", "content": ""})
        else:
            text: str | None = None
            try:
                html = _fetch_text(url, timeout)
                text = extract_topic_body(html)
            except (TimeoutError, OSError, urllib.error.HTTPError, urllib.error.URLError):
                text = None
            except Exception:
                text = None

            if text:
                out.append({**row, "state": "ok", "content": _truncate_text(text, max_content_chars)})
            else:
                out.append({**row, "state": "fail", "content": ""})

        if delay > 0 and i < n_fetch - 1:
            time.sleep(delay)

    return out


######################
# 본문 채우기 실행 흐름 관련
######################
def main() -> int:
    """
    GeekNews thread CSV에 본문을 채워 새 CSV로 저장한다.

    Returns:
        정상 종료 시 0, 입력 오류 시 1.
    """
    p = argparse.ArgumentParser(description="GeekNews CSV: article_url에서 본문 수집 → state(ok/fail), content 채움")
    default_dir = Path(__file__).resolve().parent
    p.add_argument(
        "-i",
        "--input",
        type=Path,
        default=default_dir / "thread_geeknews.csv",
        help="입력 CSV (기본: 이 폴더/thread_geeknews.csv)",
    )
    p.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="출력 CSV (기본: 입력과 같은 폴더에 <이름>_with_content.csv)",
    )
    p.add_argument("--timeout", type=float, default=CONTENT_CONFIG["timeout"], help="행당 HTTP 타임아웃(초)")
    p.add_argument("--delay", type=float, default=CONTENT_CONFIG["delay"], help="행 사이 대기(초)")
    p.add_argument("--limit", type=int, default=None, help="본문 수집할 최대 행 수")
    p.add_argument(
        "--max-content-chars",
        type=int,
        default=CONTENT_CONFIG["max_content_chars"],
        help="content 최대 글자 수(0=무제한)",
    )
    args = p.parse_args()

    inp: Path = args.input
    if not inp.is_file():
        logger.error("입력 파일 없음: %s", inp)
        return 1

    out_path: Path = args.output or inp.with_name(f"{inp.stem}_with_content{inp.suffix}")

    with inp.open(encoding=CSV_ENCODING, newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            logger.error("CSV 헤더가 없습니다.")
            return 1
        fieldnames = _merge_fieldnames(list(reader.fieldnames))
        rows = list(reader)

    # 기존 파일에 컬럼이 없더라도 후속 로직이 항상 같은 키를 다루게 만든다.
    for row in rows:
        row.setdefault("state", "")
        row.setdefault("content", "")

    enriched = enrich_rows(
        rows,
        timeout=args.timeout,
        delay=args.delay,
        limit=args.limit,
        max_content_chars=args.max_content_chars,
    )
    _write_dict_csv(out_path, fieldnames, enriched)
    return 0


def configure_logging() -> None:
    """진입점 기본 로깅 설정을 INFO 수준으로 초기화한다."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")


if __name__ == "__main__":
    configure_logging()
    raise SystemExit(main())
