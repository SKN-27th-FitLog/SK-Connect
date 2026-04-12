"""
IT 뉴스 ETL: thread 수집 → 본문 수집 → 클린징 → DB 삽입을 순차 실행한다.

레포 루트를 cwd로 두고 각 단계 스크립트를 subprocess로 호출한다.
(02_cleaning_tables/cleaning_tables.py 출력 경로가 레포 루트 기준 상대 경로이므로 cwd 고정이 필요하다.)
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

# etl/it_news/update_db_it_news.py → 레포 루트는 it_news 기준 상위 2단계
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent

_STEPS: tuple[Path, ...] = (
    _REPO_ROOT / "etl" / "it_news" / "01_getter_threads" / "gatter_thread_pytorch.py",
    _REPO_ROOT / "etl" / "it_news" / "01_getter_threads" / "gatter_thread_geeknews.py",
    _REPO_ROOT / "etl" / "it_news" / "01_getter_threads" / "gatter_content_geeknews.py",
    _REPO_ROOT / "etl" / "it_news" / "01_getter_threads" / "gatter_content_pytorch.py",
    _REPO_ROOT / "etl" / "it_news" / "02_cleaning_tables" / "cleaning_tables.py",
    _REPO_ROOT / "etl" / "it_news" / "03_insert_tables" / "insert_tables.py",
)


def _check_scripts_exist() -> list[Path]:
    """존재하지 않는 스크립트 경로만 모아 반환한다."""
    missing: list[Path] = []
    for p in _STEPS:
        if not p.is_file():
            missing.append(p)
    return missing


def main() -> int:
    missing = _check_scripts_exist()
    if missing:
        print("다음 스크립트 파일을 찾을 수 없습니다:", file=sys.stderr)
        for p in missing:
            print(f"  {p}", file=sys.stderr)
        return 1

    for script in _STEPS:
        print(f"\n--- 실행: {script.relative_to(_REPO_ROOT)} ---\n")
        subprocess.run(
            [sys.executable, str(script)],
            cwd=_REPO_ROOT,
            check=True,
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
