"""IT-L2-MRG: insert_crawling_batch 간접 (merge_mock)."""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from common.constant import CrawlingColumn, CodeTable
from postgresql.run_query import (
    INSERT_CRAWLING_FROM_JSONB_SQL,
    _normalize_map_id,
    insert_crawling_batch,
)

pytestmark = pytest.mark.merge_mock


def test_it_l2_mrg_001_empty_df_no_execute() -> None:
    """IT-L2-MRG-001: 빈 df는 execute 없음."""
    mock_db = MagicMock()
    with patch("postgresql.run_query.PostgreDB", return_value=mock_db):
        insert_crawling_batch(pd.DataFrame())
    mock_db.conn.cursor.assert_not_called()


def test_it_l2_mrg_002_merge_sql_executed(minimal_crawl_row: dict) -> None:
    """IT-L2-MRG-002: MERGE SQL 1회 execute."""
    mock_cur = MagicMock()
    mock_conn = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cur
    mock_db = MagicMock()
    mock_db.conn = mock_conn

    df = pd.DataFrame([minimal_crawl_row])

    with patch("postgresql.run_query.PostgreDB", return_value=mock_db):
        insert_crawling_batch(df)

    mock_cur.execute.assert_called_once()
    sql = mock_cur.execute.call_args[0][0]
    assert "MERGE" in sql
    assert "ON c.thread = s.thread" in INSERT_CRAWLING_FROM_JSONB_SQL


def test_it_l2_mrg_003_normalize_map_id() -> None:
    """IT-L2-MRG-003: map_id 0·NaN → None."""
    assert _normalize_map_id(0) is None
    assert _normalize_map_id(None) is None
    assert _normalize_map_id(42) == 42
