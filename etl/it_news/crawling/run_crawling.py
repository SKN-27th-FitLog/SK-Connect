"""
thread crawling 스테이지 오케스트레이터.

각 소스별 목록 수집 스크립트와 본문 보강 스크립트를 차례로 실행하고,
최종 raw 성공/실패 CSV를 정리해 다음 cleaning 단계로 넘긴다.
"""

from __future__ import annotations

import argparse
import logging
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from common.settings import get_config
from common.runtime import (
    IT_NEWS_ROOT,
    make_stage_paths,
    read_rows,
    run_python,
    source_csv_path,
    split_rows,
    write_rows,
)


######################
# 설정 기반 상수 관련
######################
CONFIG = get_config()
PATHS_CONFIG = CONFIG["paths"]
THREAD_COLLECTION_CONFIG = CONFIG["thread_collection"]
THREAD_JOBS = tuple(CONFIG["jobs"]["thread"])
_KST = ZoneInfo(CONFIG["timezone"])
THREAD_SCRIPT_ROOT = Path(__file__).resolve().parent / "thread"
logger = logging.getLogger(__name__)


######################
# 실행 인자 및 실행 시각 처리 관련
######################
def parse_args() -> argparse.Namespace:
    """
    crawling 스테이지 실행 인자를 파싱한다.

    Args:
        없음.

    Returns:
        수집 날짜, 제한 건수, 타임아웃 정보가 담긴 네임스페이스.
    """
    parser = argparse.ArgumentParser(description="IT News crawling stage runner")
    parser.add_argument("--date", default=None, help="기본값은 오늘(KST), YYYY-MM-DD 형식")
    parser.add_argument("--limit", type=int, default=THREAD_COLLECTION_CONFIG["limit"], help="사이트별 최대 수집 건수")
    parser.add_argument("--timeout", type=float, default=THREAD_COLLECTION_CONFIG["timeout"], help="목록 수집 타임아웃")
    parser.add_argument(
        "--content-timeout",
        type=float,
        default=THREAD_COLLECTION_CONFIG["content_timeout"],
        help="본문 수집 타임아웃",
    )
    parser.add_argument(
        "--content-delay",
        type=float,
        default=THREAD_COLLECTION_CONFIG["content_delay"],
        help="본문 수집 지연",
    )
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
# 임시 파일 경로 및 소스 처리 관련
######################
def build_temp_path(source: str, suffix: str, *, kind: str) -> Path:
    """
    소스별 임시 CSV 파일 경로를 생성한다.

    Args:
        source: 수집 소스 이름.
        suffix: 파일 구분용 접미사.

    Returns:
        `.tmp` 디렉터리 아래의 임시 CSV 경로.
    """
    # 목록 수집 결과와 본문 보강 결과를 분리해 저장하기 위해 `.tmp/<kind>` 하위 경로를 사용한다.
    tmp_dir = IT_NEWS_ROOT / "crawling" / PATHS_CONFIG["temp_dirname"] / kind
    tmp_dir.mkdir(parents=True, exist_ok=True)
    return tmp_dir / f"{source}_{suffix}.csv"


def process_source(
    *,
    source: str,
    thread_script: str,
    content_script: str,
    thread_filename: str,
    with_content_filename: str,
    run_at: datetime,
    args: argparse.Namespace,
) -> tuple[Path | None, Path | None]:
    """
    한 개 소스에 대해 목록 수집, 본문 수집, 성공/실패 분리를 순차 실행한다.

    Args:
        source: 수집 소스 이름.
        thread_script: 목록 수집 스크립트 파일명.
        content_script: 본문 수집 스크립트 파일명.
        thread_filename: 목록 임시 파일 접미사.
        with_content_filename: 본문 포함 임시 파일 접미사.
        run_at: 실행 기준 시각.
        args: 실행 인자 네임스페이스.

    Returns:
        성공 CSV 경로와 실패 CSV 경로. 없으면 각각 None이다.
    """
    # 한 소스의 중간 산출물과 최종 산출물을 같은 실행 시각 기준으로 정렬한다.
    raw_paths = make_stage_paths(PATHS_CONFIG["raw_bucket"], run_at, kind=PATHS_CONFIG["thread_kind"])

    thread_csv = build_temp_path(source, thread_filename, kind="thread")
    content_csv = build_temp_path(source, with_content_filename, kind="thread")

    # 1단계: 목록 수집
    run_python(
        THREAD_SCRIPT_ROOT / thread_script,
        "--limit",
        str(args.limit),
        "--timeout",
        str(args.timeout),
        "--output",
        str(thread_csv),
    )
    # 2단계: 본문 보강
    run_python(
        THREAD_SCRIPT_ROOT / content_script,
        "--input",
        str(thread_csv),
        "--output",
        str(content_csv),
        "--timeout",
        str(args.content_timeout),
        "--delay",
        str(args.content_delay),
    )

    # 3단계: 공통 검증 규칙으로 success/fail 분리
    fieldnames, rows = read_rows(content_csv)
    if source == "geeknews":
        success_rows, fail_rows = split_rows(
            rows,
            required_fields=("title", "content", "article_url", "topic_id"),
            url_field="article_url",
            id_field="topic_id",
        )
    else:
        success_rows, fail_rows = split_rows(
            rows,
            required_fields=("title", "content", "topic_url", "topic_id"),
            url_field="topic_url",
            id_field="topic_id",
        )

    success_path: Path | None = None
    fail_path: Path | None = None

    if success_rows:
        success_path = source_csv_path(raw_paths, source, run_at, ok=True)
        write_rows(success_path, fieldnames, success_rows)

    if fail_rows:
        fail_fieldnames = list(fieldnames)
        if "failure_reason" not in fail_fieldnames:
            fail_fieldnames.append("failure_reason")
        fail_path = source_csv_path(raw_paths, source, run_at, ok=False)
        write_rows(fail_path, fail_fieldnames, fail_rows)

    return success_path, fail_path


######################
# crawling 실행 흐름 관련
######################
def main() -> int:
    """
    정의된 수집 소스들을 순회하며 crawling 스테이지를 실행한다.

    Args:
        없음.

    Returns:
        정상 종료 시 0.
    """
    # 설정 기본값은 config.json에서 오지만, CLI가 들어오면 해당 실행에서만 override 된다.
    args = parse_args()
    run_at = parse_run_at(args.date)
    raw_paths = make_stage_paths(PATHS_CONFIG["raw_bucket"], run_at, kind=PATHS_CONFIG["thread_kind"])

    had_success = False
    # job 정의 자체를 설정화해 소스 추가/순서 변경 시 코드를 최소 수정하도록 구성했다.
    for job in THREAD_JOBS:
        try:
            success_path, fail_path = process_source(run_at=run_at, args=args, **job)
        except Exception as exc:
            fail_path = source_csv_path(raw_paths, job["source"], run_at, ok=False)
            write_rows(
                fail_path,
                ["source_name", "failure_reason"],
                [{"source_name": job["source"], "failure_reason": str(exc)}],
            )
            logger.error("[fail] %s -> %s", job["source"], fail_path)
            continue

        if success_path is not None:
            had_success = True
            logger.info("[ok] %s -> %s", job["source"], success_path)
        if fail_path is not None:
            logger.error("[fail] %s -> %s", job["source"], fail_path)

    if not had_success:
        raise SystemExit("수집 성공 파일이 없습니다.")

    return 0


def configure_logging() -> None:
    """진입점 기본 로깅 설정을 INFO 수준으로 초기화한다."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")


if __name__ == "__main__":
    configure_logging()
    raise SystemExit(main())
