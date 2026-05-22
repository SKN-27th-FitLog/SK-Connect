"""IT-L1-WM: postgresql.watermark Level 1 (mock)."""

from datetime import datetime
from unittest.mock import MagicMock, patch

from common.constant import Service
from common.utils import default_last_collected_at
from postgresql.watermark import get_last_success_date


def test_it_l1_wm_001_empty_db_returns_default() -> None:
    """IT-L1-WM-001: MAX NULL → default_last_collected_at."""
    mock_db = MagicMock()
    mock_db.run_query.return_value = [(None,)]

    with patch("postgresql.watermark.PostgreDB", return_value=mock_db):
        result = get_last_success_date()

    assert result == default_last_collected_at()


def test_it_l1_wm_002_service_prefix_max() -> None:
    """IT-L1-WM-002: service별 MAX(created_at)."""
    expected = datetime(2026, 5, 1, 12, 0, 0)
    mock_db = MagicMock()
    mock_db.run_query_lst.return_value = [(expected,)]

    with patch("postgresql.watermark.PostgreDB", return_value=mock_db):
        result = get_last_success_date(Service.GEEKNEWS)

    assert result == expected
    mock_db.run_query_lst.assert_called_once()
