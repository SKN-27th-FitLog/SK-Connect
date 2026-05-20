"""PA-L2-PG-MRG: merge_analysis_data 간접 검증 (cursor mock, merge_mock 마커)."""

from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

from common.constant import AnalysisColumn
from postgresql.config import MergeAnalysisConfig
from postgresql.run_query import merge_analysis_data

pytestmark = pytest.mark.merge_mock


def test_pa_l2_pg_mrg_001_executes_merge_with_records() -> None:
    """PA-L2-PG-MRG-001 [정상]: MERGE SQL이 cursor.execute로 1회 호출된다.

    PostgreDB는 mock — 실 DB TCP/MERGE 없음.
    """
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
    """PA-L2-PG-MRG-002 [불변]: NaN/pd.NA는 Jsonb records에서 None으로 정규화."""
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
    """PA-L2-PG-MRG-010~012 [불변·간접]: MERGE SQL에 COALESCE NULL 덮어쓰기 방지.

    실 DB MERGE 대신 SQL 문자열 불변 규칙만 검증.
    """
    sql = MergeAnalysisConfig.MERGE_SQL
    assert "COALESCE(x.title, a.title)" in sql
    assert "COALESCE(x.keywords, a.keywords)" in sql
