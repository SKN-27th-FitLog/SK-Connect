"""
IT 뉴스 ETL: crawling → cleaning → save 3단계를 순차 실행한다.

새 구조의 단계별 러너를 호출하고, 각 단계는 날짜별 success/fail 폴더를 직접 관리한다.
"""
from __future__ import annotations

import argparse
import logging
import subprocess
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
logger = logging.getLogger(__name__)

_THREAD_STEPS: tuple[Path, ...] = (
    _REPO_ROOT / "etl" / "it_news" / "crawling" / "run_crawling.py",
    _REPO_ROOT / "etl" / "it_news" / "cleaning" / "run_cleaning.py",
    _REPO_ROOT / "etl" / "it_news" / "save" / "run_save.py",
)
_COMMENT_STEPS: tuple[Path, ...] = (
    _REPO_ROOT / "etl" / "it_news" / "crawling" / "run_comment_crawling.py",
    _REPO_ROOT / "etl" / "it_news" / "cleaning" / "run_comment_cleaning.py",
    _REPO_ROOT / "etl" / "it_news" / "save" / "run_comment_save.py",
)


######################
# 실행 대상 확인 관련
######################
def _check_scripts_exist(steps: tuple[Path, ...]) -> list[Path]:
    """
    선택된 파이프라인 단계 스크립트가 모두 존재하는지 확인한다.

    Args:
        steps: 실행 예정인 스크립트 경로 목록.

    Returns:
        실제 파일이 없는 스크립트 경로 목록.
    """
    missing: list[Path] = []
    for p in steps:
        if not p.is_file():
            missing.append(p)
    return missing


def parse_args() -> argparse.Namespace:
    """
    진입점 CLI 인자를 파싱한다.

    Returns:
        실행 날짜, 대상 파이프라인, comment 저장용 사용자 ID가 담긴 네임스페이스.
    """
    parser = argparse.ArgumentParser(description="IT News ETL pipeline runner")
    parser.add_argument("--date", default=None, help="기본값은 오늘(KST), YYYY-MM-DD 형식")
    parser.add_argument(
        "--targets",
        nargs="+",
        choices=("thread", "comment"),
        default=("thread",),
        help="실행할 파이프라인 대상. 기본값은 thread",
    )
    parser.add_argument(
        "--comment-user-id",
        type=int,
        default=None,
        help="comment save 단계에서 comments.user_id 로 사용할 기본 사용자 ID",
    )
    return parser.parse_args()


######################
# 실행 단계 조립 관련
######################
def selected_steps(targets: list[str]) -> tuple[Path, ...]:
    """
    사용자가 고른 대상(thread/comment)에 맞춰 실제 실행 순서를 만든다.

    Args:
        targets: 실행할 파이프라인 대상 목록.

    Returns:
        순차 실행할 스크립트 경로 튜플.
    """
    steps: list[Path] = []
    if "thread" in targets:
        steps.extend(_THREAD_STEPS)
    if "comment" in targets:
        steps.extend(_COMMENT_STEPS)
    return tuple(steps)


######################
# 파이프라인 실행 관련
######################
def main() -> int:
    """
    선택된 ETL 단계를 순차 실행한다.

    Returns:
        정상 종료 시 0, 스크립트 누락 시 1.
    """
    args = parse_args()
    steps = selected_steps(list(args.targets))
    missing = _check_scripts_exist(steps)
    if missing:
        logger.error("다음 스크립트 파일을 찾을 수 없습니다:")
        for p in missing:
            logger.error("  %s", p)
        return 1

    for script in steps:
        logger.info("--- 실행: %s ---", script.relative_to(_REPO_ROOT))
        command = [sys.executable, str(script)]
        if args.date:
            command.extend(["--date", args.date])
        if script.name == "run_comment_save.py" and args.comment_user_id is not None:
            command.extend(["--user-id", str(args.comment_user_id)])
        subprocess.run(
            command,
            cwd=_REPO_ROOT,
            check=True,
        )

    return 0


def configure_logging() -> None:
    """진입점 기본 로깅 설정을 INFO 수준으로 초기화한다."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")


if __name__ == "__main__":
    configure_logging()
    raise SystemExit(main())
