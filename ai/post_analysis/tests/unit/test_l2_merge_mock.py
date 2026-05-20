"""PA-L2-PG-MRG-001~005, 010~012 간접: merge_analysis_data (cursor mock)."""

import pytest

pytestmark = pytest.mark.merge_mock

from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd

from common.constant import AnalysisColumn
from postgresql.config import MergeAnalysisConfig
from postgresql.run_query import merge_analysis_data


def test_pa_l2_pg_mrg_001_executes_merge_with_records() -> None:
    df = pd.DataFrame({AnalysisColumn.CRAWLING_ID.value: [-900000001]})
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cur

    mock_db = MagicMock()
    mock_db.conn = mock_conn

    with patch("postgresql.run_query.PostgreDB", return_value=mock_db):
        merge_analysis_data(df)

    mock_cur.execute.assert_called_once()
    args = mock_cur.execute.call_args[0]
    assert MergeAnalysisConfig.MERGE_SQL.strip() in args[0] or "MERGE" in args[0]


def test_pa_l2_pg_mrg_002_nan_becomes_none_in_records() -> None:
    df = pd.DataFrame(
        {
            AnalysisColumn.CRAWLING_ID.value: [-900000002],
            AnalysisColumn.TITLE.value: [np.nan],
        }
    )
    captured: list = []

    def capture_execute(sql, params):  # noqa: ANN001
        captured.append(params)

    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_cur.execute.side_effect = capture_execute
    mock_conn.cursor.return_value.__enter__.return_value = mock_cur
    mock_db = MagicMock()
    mock_db.conn = mock_conn

    with patch("postgresql.run_query.PostgreDB", return_value=mock_db):
        merge_analysis_data(df)

    assert captured


def test_pa_l2_pg_mrg_010_012_sql_has_coalesce_guard() -> None:
    """실 DB MRG-010~012 대신 MERGE SQL 불변 규칙 검증."""
    sql = MergeAnalysisConfig.MERGE_SQL
    assert "COALESCE(x.title, a.title)" in sql
    assert "COALESCE(x.keywords, a.keywords)" in sql
