from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from common.runtime import make_stage_paths, raw_success_files, read_rows, source_csv_path, write_rows

_KST = ZoneInfo("Asia/Seoul")
SUCCESS_FIELDS = [
    "post_id",
    "crawling_id",
    "thread",
    "content",
    "created_at",
    "modify_at",
    "status_cd",
    "source_name",
    "source_file",
]
FAIL_FIELDS = SUCCESS_FIELDS + ["failure_reason"]


######################
# 실행 인자 및 실행 시각 처리 관련
######################
def parse_args() -> argparse.Namespace:
    """
    comment cleaning 단계 실행 인자를 파싱한다.

    Returns:
        실행 날짜와 기본 상태 코드가 담긴 argparse 네임스페이스.
    """
    parser = argparse.ArgumentParser(description="IT News comment cleaning stage runner")
    parser.add_argument("--date", default=None, help="기본값은 오늘(KST), YYYY-MM-DD 형식")
    parser.add_argument("--status-cd", default="ST01", help="comments 테이블 기본 상태 코드")
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
# 파일명 및 행 정규화 관련
######################
def infer_source_name(path: Path) -> str:
    """
    comment raw 파일명에서 수집 소스 이름을 추론한다.

    Args:
        path: comment raw CSV 경로.

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
    raise ValueError(f"지원하지 않는 comment raw 파일 이름입니다: {path.name}")


def normalize_row(
    row: dict[str, str],
    *,
    source_name: str,
    source_file: str,
    status_cd: str,
) -> tuple[dict[str, Any], str | None]:
    """
    comment raw 한 행을 comments 적재용 형식으로 정리하고 검증한다.

    Args:
        row: 원본 CSV 행 데이터.
        source_name: 수집 소스 이름.
        source_file: 현재 처리 중인 원본 파일명.
        status_cd: 기본 댓글 상태 코드.

    Returns:
        정규화된 행 데이터와 실패 사유 문자열.
    """
    reasons: list[str] = []
    content = (row.get("content") or "").strip()
    created_at = (row.get("created_at") or "").strip()
    modify_at = (row.get("modify_at") or created_at).strip()
    thread = (row.get("thread") or "").strip()
    crawling_id = (row.get("crawling_id") or "").strip()

    if not thread:
        reasons.append("missing_thread")
    if not crawling_id:
        reasons.append("missing_crawling_id")
    else:
        try:
            int(crawling_id)
        except ValueError:
            reasons.append("invalid_crawling_id")
    if not content:
        reasons.append("missing_content")
    if not created_at:
        reasons.append("missing_created_at")
    else:
        try:
            datetime.fromisoformat(created_at)
        except ValueError:
            reasons.append("invalid_created_at")
    if not modify_at:
        reasons.append("missing_modify_at")
    else:
        try:
            datetime.fromisoformat(modify_at)
        except ValueError:
            reasons.append("invalid_modify_at")

    normalized = {
        "post_id": "",
        "crawling_id": crawling_id,
        "thread": thread,
        "content": content,
        "created_at": created_at,
        "modify_at": modify_at,
        "status_cd": status_cd,
        "source_name": source_name,
        "source_file": source_file,
    }
    return normalized, "|".join(reasons) if reasons else None


######################
# comment cleaning 실행 흐름 관련
######################
def main() -> int:
    """
    comment raw 성공 파일을 읽어 comments 적재용 성공/실패 CSV로 분리 저장한다.

    Returns:
        정상 종료 시 0.
    """
    args = parse_args()
    run_at = parse_run_at(args.date)
    cleaning_paths = make_stage_paths("cleaning", run_at, kind="comment")
    files = raw_success_files(run_at, kind="comment")
    if not files:
        raise SystemExit("cleaning 대상 comment raw 성공 파일이 없습니다.")

    # 같은 실행 배치 안에서 완전히 동일한 댓글은 한 번만 남긴다.
    seen_keys: set[tuple[str, str, str]] = set()
    for file_path in files:
        source_name = infer_source_name(file_path)
        _, rows = read_rows(file_path)
        success_rows: list[dict[str, Any]] = []
        fail_rows: list[dict[str, Any]] = []

        for row in rows:
            normalized, failure_reason = normalize_row(
                row,
                source_name=source_name,
                source_file=file_path.name,
                status_cd=args.status_cd,
            )
            if failure_reason:
                fail_rows.append({**normalized, "failure_reason": failure_reason})
                continue

            key = (
                str(normalized["crawling_id"]),
                str(normalized["created_at"]),
                str(normalized["content"]),
            )
            if key in seen_keys:
                fail_rows.append({**normalized, "failure_reason": "duplicate_comment"})
                continue

            seen_keys.add(key)
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
