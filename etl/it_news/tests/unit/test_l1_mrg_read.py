"""IT-L1-MRG: fetch_crawling_dataframe Level 1 (mock)."""

from unittest.mock import MagicMock, patch

from common.constant import CrawlingColumn
from postgresql.run_query import fetch_crawling_dataframe


def test_it_l1_mrg_001_fetch_crawling_dataframe() -> None:
    """IT-L1-MRG-001: thread 컬럼 SELECT → DataFrame."""
    mock_cur = MagicMock()
    mock_cur.fetchall.return_value = [("geeknews_1",), ("pytorch_2",)]
    mock_conn = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cur
    mock_db = MagicMock()
    mock_db.conn = mock_conn

    with patch("postgresql.run_query.PostgreDB", return_value=mock_db):
        df = fetch_crawling_dataframe(CrawlingColumn.THREAD)

    assert list(df[CrawlingColumn.THREAD.value]) == ["geeknews_1", "pytorch_2"]
