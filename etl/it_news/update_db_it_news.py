"""
IT 뉴스 ETL: crawling → cleaning → save 3단계를 순차 실행한다.

새 구조의 단계별 러너를 호출하고, 각 단계는 날짜별 success/fail 폴더를 직접 관리한다.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent

_STEPS: tuple[Path, ...] = (
    _REPO_ROOT / "etl" / "it_news" / "crawling" / "run_crawling.py",
    _REPO_ROOT / "etl" / "it_news" / "cleaning" / "run_cleaning.py",
    _REPO_ROOT / "etl" / "it_news" / "save" / "run_save.py",
)


def _check_scripts_exist() -> list[Path]:
    missing: list[Path] = []
    for p in _STEPS:
        if not p.is_file():
            missing.append(p)
    return missing


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="IT News ETL pipeline runner")
    parser.add_argument("--date", default=None, help="기본값은 오늘(KST), YYYY-MM-DD 형식")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    missing = _check_scripts_exist()
    if missing:
        print("다음 스크립트 파일을 찾을 수 없습니다:", file=sys.stderr)
        for p in missing:
            print(f"  {p}", file=sys.stderr)
        return 1

    for script in _STEPS:
        print(f"\n--- 실행: {script.relative_to(_REPO_ROOT)} ---\n")
        command = [sys.executable, str(script)]
        if args.date:
            command.extend(["--date", args.date])
        subprocess.run(
            command,
            cwd=_REPO_ROOT,
            check=True,
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
