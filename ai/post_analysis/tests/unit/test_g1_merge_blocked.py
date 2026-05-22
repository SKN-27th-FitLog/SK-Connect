"""G1: pytest 기본 실행 시 analysis MERGE 실호출 차단 (docs/testing.md G1)."""

import pandas as pd
import pytest

import postgresql.run_query as run_query


def test_merge_blocked_by_default() -> None:
    """G1: merge_analysis_data 직접 호출 시 RuntimeError로 차단된다.

    실 DB에 INSERT/UPDATE가 나가지 않음을 보장한다.
    """
    with pytest.raises(RuntimeError, match="blocked during tests"):
        run_query.merge_analysis_data(pd.DataFrame({"crawling_id": [-1]}))
