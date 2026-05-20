"""G1: 기본 테스트에서 merge 실호출 차단 확인."""

import pandas as pd
import pytest

import postgresql.run_query as run_query


def test_merge_blocked_by_default() -> None:
    with pytest.raises(RuntimeError, match="blocked during tests"):
        run_query.merge_analysis_data(pd.DataFrame({"crawling_id": [-1]}))
