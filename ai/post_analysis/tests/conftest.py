"""pytest 가드레일 — merge_analysis_data 실실행 차단 (docs/testing.md G1)."""

from __future__ import annotations

import os

import postgresql.run_query as _run_query
import pytest

MERGE_BLOCKED_MSG = (
    "merge_analysis_data is blocked during tests (docs/testing.md G1). "
    "Patch merge or set POST_ANALYSIS_TEST_BLOCK_MERGE=0 only for local manual runs."
)

_ORIGINAL_MERGE = _run_query.merge_analysis_data


def _merge_blocked(df) -> None:  # noqa: ANN001
    raise RuntimeError(MERGE_BLOCKED_MSG)


def _should_block_merge() -> bool:
    return os.environ.get("POST_ANALYSIS_TEST_BLOCK_MERGE", "1") != "0"


@pytest.fixture(autouse=True)
def block_merge_writes(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch) -> None:
    """모든 테스트에서 analysis MERGE 실경로 차단 (`merge_mock` 제외)."""
    if request.node.get_closest_marker("merge_mock"):
        return
    if not _should_block_merge():
        return
    targets = (
        "postgresql.run_query.merge_analysis_data",
        "get_reviews.merge_analysis_data",
        "analyze_sentimental.merge_analysis_data",
        "analyze_keywords_by_llm.merge_analysis_data",
    )
    for target in targets:
        monkeypatch.setattr(target, _merge_blocked)


@pytest.fixture
def reset_singletons() -> None:
    """프로세스 내 Singleton 캐시 초기화."""
    from common.singleton import Singleton
    from postgresql.connection import PostgreDB

    Singleton._instances.clear()
    PostgreDB._instances.clear()  # type: ignore[attr-defined]
    yield
    Singleton._instances.clear()
    PostgreDB._instances.clear()  # type: ignore[attr-defined]
