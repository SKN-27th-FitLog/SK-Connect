"""PA-L0-PLN: _parse_args."""

import sys
from unittest.mock import patch

from pipeline import _parse_args


def test_pa_l0_pln_001_default_max_rows_none() -> None:
    with patch.object(sys, "argv", ["pipeline.py"]):
        assert _parse_args().max_rows is None


def test_pa_l0_pln_002_max_rows_from_cli() -> None:
    with patch.object(sys, "argv", ["pipeline.py", "--max-rows", "5"]):
        assert _parse_args().max_rows == 5


def test_pa_l0_pln_003_max_rows_one() -> None:
    with patch.object(sys, "argv", ["pipeline.py", "--max-rows", "1"]):
        assert _parse_args().max_rows == 1
