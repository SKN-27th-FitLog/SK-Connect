from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from common.runtime import (
    fallback_cutoff,
    fetch_last_created_at,
    make_stage_paths,
    raw_success_files,
    read_rows,
    source_csv_path,
    write_rows,
)


_KST = ZoneInfo("Asia/Seoul")
SUCCESS_FIELDS = [
    "title",
    "content",
    "thread",
    "article_url",
    "created_at",
    "view_count",
    "comment_count",
    "point",
    "author",
    "map_id",
    "category_cd",
    "source_name",
    "source_file",
]
FAIL_FIELDS = SUCCESS_FIELDS + ["failure_reason"]


######################
# 실행 인자 및 실행 시각 처리 관련
######################
def parse_args() -> argparse.Namespace:
    """
    cleaning 스테이지 실행 인자를 파싱한다.

    Args:
        없음.

    Returns:
        실행 날짜를 포함한 argparse 네임스페이스.
    """
    parser = argparse.ArgumentParser(description="IT News cleaning stage runner")
    parser.add_argument("--date", default=None, help="기본값은 오늘(KST), YYYY-MM-DD 형식")
    return parser.parse_args()


def parse_run_at(date_arg: str | None) -> datetime:
    """
    입력된 날짜 문자열을 KST 기준 실행 시각으로 변환한다.

    Args:
        date_arg: YYYY-MM-DD 형식의 날짜 문자열. 없으면 현재 시각을 사용한다.

    Returns:
        KST timezone 정보가 포함된 datetime 객체.
    """
    if not date_arg:
        return datetime.now(_KST)
    return datetime.strptime(date_arg, "%Y-%m-%d").replace(tzinfo=_KST)


######################
# 값 변환 및 문자열 정리 관련
######################
def to_int(value: str | None, default: int | None = None) -> int | None:
    """
    문자열 값을 정수로 변환하고 실패 시 기본값을 반환한다.

    Args:
        value: 변환 대상 문자열 값.
        default: 변환 실패 또는 빈 값일 때 사용할 기본값.

    Returns:
        변환된 정수 또는 기본값.
    """
    if value in (None, ""):
        return default
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def to_float(value: str | None, default: float | None = None) -> float | None:
    """
    문자열 값을 실수로 변환하고 실패 시 기본값을 반환한다.

    Args:
        value: 변환 대상 문자열 값.
        default: 변환 실패 또는 빈 값일 때 사용할 기본값.

    Returns:
        변환된 실수 또는 기본값.
    """
    if value in (None, ""):
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def trim_text(value: str | None, limit: int) -> str:
    """
    문자열의 앞뒤 공백을 제거하고 최대 길이까지만 잘라낸다.

    Args:
        value: 정리할 원본 문자열.
        limit: 허용할 최대 문자열 길이.

    Returns:
        정리 및 길이 제한이 적용된 문자열.
    """
    text = (value or "").strip()
    return text[:limit]


######################
# 소스별 정규화 및 검증 관련
######################
def normalize_geeknews(row: dict[str, str], source_file: str) -> tuple[dict[str, Any] | None, str | None]:
    """
    GeekNews 원본 행을 저장 스키마에 맞는 형태로 정규화한다.

    Args:
        row: 원본 CSV 한 행 데이터.
        source_file: 현재 처리 중인 원본 파일명.

    Returns:
        정규화 결과와 실패 사유 문자열. 실패 사유가 없으면 두 번째 값은 None이다.
    """
    reasons: list[str] = []
    topic_id = (row.get("topic_id") or "").strip()
    title = trim_text(row.get("title"), 200)
    content = trim_text(row.get("content"), 4000)
    article_url = trim_text(row.get("article_url"), 500)
    created_at = (row.get("posted_at") or "").strip()
    author = trim_text(row.get("author_display_name") or row.get("author_user_id"), 100)

    if (row.get("state") or "").strip() != "ok":
        reasons.append("state_not_ok")
    if not topic_id:
        reasons.append("missing_topic_id")
    if not title:
        reasons.append("missing_title")
    if not content:
        reasons.append("missing_content")
    if not article_url:
        reasons.append("missing_article_url")
    if not created_at:
        reasons.append("missing_created_at")

    normalized = {
        "title": title,
        "content": content,
        "thread": f"geek_{topic_id}" if topic_id else "",
        "article_url": article_url,
        "created_at": created_at,
        "view_count": 0,
        "comment_count": to_int(row.get("comment_count"), 0),
        "point": to_float(row.get("points"), 0.0),
        "author": author,
        "map_id": "",
        "category_cd": "CA07",
        "source_name": "geeknews",
        "source_file": source_file,
    }
    return (normalized, None) if not reasons else (normalized, "|".join(reasons))


def normalize_pytorch(row: dict[str, str], source_file: str) -> tuple[dict[str, Any] | None, str | None]:
    """
    PyTorch 포럼 원본 행을 저장 스키마에 맞는 형태로 정규화한다.

    Args:
        row: 원본 CSV 한 행 데이터.
        source_file: 현재 처리 중인 원본 파일명.

    Returns:
        정규화 결과와 실패 사유 문자열. 실패 사유가 없으면 두 번째 값은 None이다.
    """
    reasons: list[str] = []
    topic_id = (row.get("topic_id") or "").strip()
    title = trim_text(row.get("title"), 200)
    content = trim_text(row.get("content"), 4000)
    article_url = trim_text(row.get("topic_url"), 500)
    created_at = (row.get("created_at") or "").strip()
    author = trim_text(row.get("last_poster_username"), 100)

    if (row.get("state") or "").strip() != "ok":
        reasons.append("state_not_ok")
    if not topic_id:
        reasons.append("missing_topic_id")
    if not title:
        reasons.append("missing_title")
    if not content:
        reasons.append("missing_content")
    if not article_url:
        reasons.append("missing_topic_url")
    if not created_at:
        reasons.append("missing_created_at")

    normalized = {
        "title": title,
        "content": content,
        "thread": f"pyto_{topic_id}" if topic_id else "",
        "article_url": article_url,
        "created_at": created_at,
        "view_count": to_int(row.get("views"), 0),
        "comment_count": to_int(row.get("reply_count"), 0),
        "point": 0.0,
        "author": author,
        "map_id": "",
        "category_cd": "CA07",
        "source_name": "pytorch",
        "source_file": source_file,
    }
    return (normalized, None) if not reasons else (normalized, "|".join(reasons))


def normalize_row(source_name: str, row: dict[str, str], source_file: str) -> tuple[dict[str, Any] | None, str | None]:
    """
    소스 이름에 따라 적절한 정규화 함수를 선택해 호출한다.

    Args:
        source_name: 데이터 수집 소스 이름.
        row: 원본 CSV 한 행 데이터.
        source_file: 현재 처리 중인 원본 파일명.

    Returns:
        정규화 결과와 실패 사유 문자열.
    """
    if source_name == "geeknews":
        return normalize_geeknews(row, source_file)
    if source_name == "pytorch":
        return normalize_pytorch(row, source_file)
    return None, "unknown_source"


def infer_source_name(path: Path) -> str:
    """
    파일명 규칙을 기반으로 원본 데이터의 소스 이름을 추론한다.

    Args:
        path: 원본 CSV 파일 경로.

    Returns:
        추론된 소스 이름.

    Raises:
        ValueError: 지원하지 않는 파일명 패턴일 때 발생한다.
    """
    stem = path.stem.lower()
    if stem.startswith("geeknews_"):
        return "geeknews"
    if stem.startswith("pytorch_"):
        return "pytorch"
    raise ValueError(f"지원하지 않는 raw 파일 이름입니다: {path.name}")


def is_newer_than_cutoff(created_at: str, cutoff: datetime) -> bool:
    """
    게시글 생성 시각이 증분 적재 기준 시각보다 최신인지 확인한다.

    Args:
        created_at: ISO 형식의 생성 시각 문자열.
        cutoff: 비교 기준이 되는 시각.

    Returns:
        기준 시각보다 최신이면 True, 아니면 False.
    """
    try:
        created = datetime.fromisoformat(created_at)
    except ValueError:
        return False

    if created.tzinfo is None:
        created = created.replace(tzinfo=_KST)
    return created.astimezone(_KST) > cutoff.astimezone(_KST)


######################
# cleaning 실행 흐름 관련
######################
def main() -> int:
    """
    raw 성공 파일을 정규화하고 성공/실패 결과로 분리 저장한다.

    Args:
        없음.

    Returns:
        정상 종료 시 0.
    """
    args = parse_args()
    run_at = parse_run_at(args.date)
    cleaning_paths = make_stage_paths("cleaning", run_at)
    cutoff = fetch_last_created_at() or fallback_cutoff(run_at)
    seen_article_urls: set[str] = set()

    files = raw_success_files(run_at)
    if not files:
        raise SystemExit("cleaning 대상 raw 성공 파일이 없습니다.")

    for file_path in files:
        source_name = infer_source_name(file_path)
        _, rows = read_rows(file_path)
        success_rows: list[dict[str, Any]] = []
        fail_rows: list[dict[str, Any]] = []

        for row in rows:
            normalized, failure_reason = normalize_row(source_name, row, file_path.name)
            if normalized is None:
                fail_rows.append({"source_file": file_path.name, "failure_reason": failure_reason or "normalize_failed"})
                continue

            article_url = normalized["article_url"]
            if failure_reason:
                fail_rows.append({**normalized, "failure_reason": failure_reason})
                continue
            if article_url in seen_article_urls:
                fail_rows.append({**normalized, "failure_reason": "duplicate_article_url"})
                continue
            if not is_newer_than_cutoff(str(normalized["created_at"]), cutoff):
                fail_rows.append({**normalized, "failure_reason": "older_than_cutoff"})
                continue

            seen_article_urls.add(article_url)
            success_rows.append(normalized)

        success_path = source_csv_path(cleaning_paths, file_path.name, ok=True)
        fail_path = source_csv_path(cleaning_paths, file_path.name, ok=False)

        if success_rows:
            write_rows(success_path, SUCCESS_FIELDS, success_rows)
            print(f"[ok] {file_path.name} -> {success_path}")
        if fail_rows:
            write_rows(fail_path, FAIL_FIELDS, fail_rows)
            print(f"[fail] {file_path.name} -> {fail_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
