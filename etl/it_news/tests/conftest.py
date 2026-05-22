"""pytest 가드레일 및 공통 fixture (docs/testing.md G1~G5)."""

from __future__ import annotations

import os
from datetime import date, datetime
from pathlib import Path

import pandas as pd
import pytest

import postgresql.run_query as _run_query

MERGE_BLOCKED_MSG = (
    "insert_crawling_batch is blocked during tests (docs/testing.md G1). "
    "Use merge_mock marker with PostgreDB mock, or set IT_NEWS_TEST_BLOCK_MERGE=0 "
    "only for local manual runs."
)

_ORIGINAL_INSERT = _run_query.insert_crawling_batch


def _insert_blocked(df) -> None:  # noqa: ANN001
    raise RuntimeError(MERGE_BLOCKED_MSG)


def _should_block_merge() -> bool:
    return os.environ.get("IT_NEWS_TEST_BLOCK_MERGE", "1") != "0"


@pytest.fixture(autouse=True)
def block_crawling_merge_writes(
    request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch
) -> None:
    """G1: 기본 테스트에서 crawling MERGE 실경로 차단 (`merge_mock` 마커 제외)."""
    if request.node.get_closest_marker("merge_mock"):
        return
    if not _should_block_merge():
        return
    targets = (
        "postgresql.run_query.insert_crawling_batch",
        "save.save.insert_crawling_batch",
    )
    for target in targets:
        monkeypatch.setattr(target, _insert_blocked)


@pytest.fixture
def reset_singletons() -> None:
    """G5: PostgreDB 싱글톤 캐시 초기화."""
    from postgresql.connection import PostgreDB
    from postgresql.singleton import Singleton

    Singleton._instances.clear()
    PostgreDB._instances.clear()  # type: ignore[attr-defined]
    yield
    Singleton._instances.clear()
    PostgreDB._instances.clear()  # type: ignore[attr-defined]


@pytest.fixture
def fixed_now() -> datetime:
    return datetime(2026, 5, 20, 11, 30, 45)


@pytest.fixture
def minimal_crawl_row() -> dict[str, object]:
    from common.constant import CodeTable, CrawlingColumn

    c = CrawlingColumn
    return {
        c.TITLE.value: "제목",
        c.CONTENT.value: "본문",
        c.ARTICLE_URL.value: "https://example.com/t/1",
        c.CREATED_AT.value: "2026-05-20 10:00:00",
        c.THREAD.value: "geeknews_1",
        c.CATEGORY_CD.value: CodeTable.CATEGORY_ETC.value,
        c.INFORMATION_CD.value: CodeTable.INFORMATION_IT.value,
    }


def write_success_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(path, index=False, encoding="utf-8")


def build_raw_csv_path(
    root: Path,
    *,
    service: str,
    run_date: date,
    hhmmss: str = "120000",
    information_cd: str = "IC02",
) -> Path:
    return (
        root
        / "process=raw"
        / f"information_cd={information_cd}"
        / f"year={run_date.year:04d}"
        / f"month={run_date.month:02d}"
        / f"day={run_date.day:02d}"
        / "status=success"
        / f"{service}_{hhmmss}.csv"
    )


def build_cleaning_csv_path(
    root: Path,
    *,
    run_date: date,
    hhmmss: str = "120000",
    information_cd: str = "IC02",
    prefix: str = "it_news",
) -> Path:
    return (
        root
        / "process=cleaning"
        / f"information_cd={information_cd}"
        / f"year={run_date.year:04d}"
        / f"month={run_date.month:02d}"
        / f"day={run_date.day:02d}"
        / "status=success"
        / f"{prefix}_{hhmmss}.csv"
    )
