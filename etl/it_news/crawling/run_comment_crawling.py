from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from common.runtime import make_stage_paths, run_python, source_csv_path, write_rows

_KST = ZoneInfo("Asia/Seoul")


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
    parser.add_argument("--timeout", type=float, default=45.0, help="댓글 수집 타임아웃")
    parser.add_argument("--sleep-seconds", type=float, default=0.75, help="요청 사이 대기 시간")
    parser.add_argument("--max-comments", type=int, default=500, help="GeekNews 토픽당 최대 댓글 수")
    parser.add_argument("--max-replies", type=int, default=500, help="PyTorch 토픽당 최대 댓글 수")
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
    raw_paths = make_stage_paths("raw", run_at, kind="comment")
    script_root = Path(__file__).resolve().parent / "comment"

    # 사이트별로 같은 실행 계약을 맞추기 위해 스크립트와 추가 인자를 표로 정의한다.
    jobs = (
        {
            "source": "geeknews",
            "script": "gatter_reply_geeknews.py",
            "extra_args": ["--max-comments", str(args.max_comments)],
        },
        {
            "source": "pytorch",
            "script": "gatter_reply_pytorch.py",
            "extra_args": ["--max-replies", str(args.max_replies)],
        },
    )

    had_success = False
    for job in jobs:
        success_path = source_csv_path(raw_paths, job["source"], run_at, ok=True)
        try:
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
            command_args.extend(job["extra_args"])
            run_python(script_root / job["script"], *command_args)
            had_success = True
            print(f"[ok] {job['source']} -> {success_path}")
        except Exception as exc:
            fail_path = source_csv_path(raw_paths, job["source"], run_at, ok=False)
            write_rows(
                fail_path,
                ["source_name", "failure_reason"],
                [{"source_name": job["source"], "failure_reason": str(exc)}],
            )
            print(f"[fail] {job['source']} -> {fail_path}")

    if not had_success:
        raise SystemExit("댓글 수집 성공 파일이 없습니다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
