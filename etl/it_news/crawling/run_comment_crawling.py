"""
comment crawling 스테이지 오케스트레이터.

DB에 저장된 게시글을 기준으로 소스별 댓글 수집 스크립트를 호출하고,
comment raw 성공/실패 CSV를 생성해 다음 cleaning 단계로 넘긴다.
"""

from __future__ import annotations

import argparse
import logging
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from common.settings import get_config
from common.runtime import make_stage_paths, run_python, source_csv_path, write_rows

######################
# 설정 기반 상수 관련
######################
CONFIG = get_config()
PATHS_CONFIG = CONFIG["paths"]
COMMENT_COLLECTION_CONFIG = CONFIG["comment_collection"]
COMMENT_JOBS = tuple(CONFIG["jobs"]["comment"])
_KST = ZoneInfo(CONFIG["timezone"])
logger = logging.getLogger(__name__)


######################
# 실행 인자 및 실행 시각 처리 관련
######################
def parse_args() -> argparse.Namespace:
    """
    comment crawling 단계 실행 인자를 파싱한다.

    Returns:
        실행 날짜와 댓글 수집 옵션이 담긴 argparse 네임스페이스.
    """
    parser = argparse.ArgumentParser(description="IT News comment crawling stage runner")
    parser.add_argument("--date", default=None, help="기본값은 오늘(KST), YYYY-MM-DD 형식")
    parser.add_argument("--limit-topics", type=int, default=None, help="사이트별 최대 대상 게시글 수")
    parser.add_argument("--timeout", type=float, default=COMMENT_COLLECTION_CONFIG["timeout"], help="댓글 수집 타임아웃")
    parser.add_argument(
        "--sleep-seconds",
        type=float,
        default=COMMENT_COLLECTION_CONFIG["sleep_seconds"],
        help="요청 사이 대기 시간",
    )
    parser.add_argument(
        "--max-comments",
        type=int,
        default=COMMENT_COLLECTION_CONFIG["max_comments"],
        help="GeekNews 토픽당 최대 댓글 수",
    )
    parser.add_argument(
        "--max-replies",
        type=int,
        default=COMMENT_COLLECTION_CONFIG["max_replies"],
        help="PyTorch 토픽당 최대 댓글 수",
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
# comment crawling 실행 흐름 관련
######################
def main() -> int:
    """
    사이트별 댓글 수집 스크립트를 순차 호출해 comment raw 산출물을 만든다.

    Returns:
        정상 종료 시 0.
    """
    args = parse_args()
    run_at = parse_run_at(args.date)
    raw_paths = make_stage_paths(PATHS_CONFIG["raw_bucket"], run_at, kind=PATHS_CONFIG["comment_kind"])
    script_root = Path(__file__).resolve().parent / "comment"

    # 소스별 추가 인자 구조는 다르지만, 공통 실행 계약(output/timeout/sleep)은 동일하다.
    had_success = False
    for job in COMMENT_JOBS:
        success_path = source_csv_path(raw_paths, job["source"], run_at, ok=True)
        try:
            limit_option = f"--{job['limit_arg']}"
            limit_value = args.max_comments if job["limit_arg"] == "max-comments" else args.max_replies
            command_args = [
                "--output",
                str(success_path),
                "--timeout",
                str(args.timeout),
                "--sleep-seconds",
                str(args.sleep_seconds),
            ]
            if args.limit_topics is not None:
                command_args.extend(["--limit-topics", str(args.limit_topics)])
            command_args.extend([limit_option, str(limit_value)])
            run_python(script_root / job["script"], *command_args)
            had_success = True
            logger.info("[ok] %s -> %s", job["source"], success_path)
        except Exception as exc:
            fail_path = source_csv_path(raw_paths, job["source"], run_at, ok=False)
            write_rows(
                fail_path,
                ["source_name", "failure_reason"],
                [{"source_name": job["source"], "failure_reason": str(exc)}],
            )
            logger.error("[fail] %s -> %s", job["source"], fail_path)

    if not had_success:
        raise SystemExit("댓글 수집 성공 파일이 없습니다.")
    return 0


def configure_logging() -> None:
    """진입점 기본 로깅 설정을 INFO 수준으로 초기화한다."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")


if __name__ == "__main__":
    configure_logging()
    raise SystemExit(main())
