"""G1: pytest 기본 실행 시 crawling MERGE 실호출 차단 (docs/testing.md G1)."""

import pandas as pd
import pytest

import postgresql.run_query as run_query


def test_it_l1_g1_001_insert_blocked_by_default() -> None:
    """IT-L1-G1-001: insert_crawling_batch 직접 호출 시 RuntimeError로 차단된다."""
    with pytest.raises(RuntimeError, match="blocked during tests"):
        run_query.insert_crawling_batch(
            pd.DataFrame({"thread": ["geeknews_test"]})
        )


def test_it_l1_g1_002_block_merge_default_env() -> None:
    """IT-L1-G1-002: IT_NEWS_TEST_BLOCK_MERGE 기본값은 차단(1)."""
    from tests.conftest import _should_block_merge

    assert _should_block_merge() is True
