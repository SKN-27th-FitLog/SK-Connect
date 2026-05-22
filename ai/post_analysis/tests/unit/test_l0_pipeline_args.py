"""PA-L0-PLN: pipeline._parse_args (Level 0)."""

import sys
from unittest.mock import patch

from pipeline import _parse_args


def test_pa_l0_pln_001_default_max_rows_none() -> None:
    """PA-L0-PLN-001 [정상]: CLI 인자 없으면 max_rows=None."""
    with patch.object(sys, "argv", ["pipeline.py"]):
        assert _parse_args().max_rows is None


def test_pa_l0_pln_002_max_rows_from_cli() -> None:
    """PA-L0-PLN-002 [정상]: --max-rows 5 파싱."""
    with patch.object(sys, "argv", ["pipeline.py", "--max-rows", "5"]):
        assert _parse_args().max_rows == 5


def test_pa_l0_pln_003_max_rows_one() -> None:
    """PA-L0-PLN-003 [경계]: --max-rows 1 파싱."""
    with patch.object(sys, "argv", ["pipeline.py", "--max-rows", "1"]):
        assert _parse_args().max_rows == 1
