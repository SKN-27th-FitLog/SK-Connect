"""IT-L0-CFG: postgresql.config Level 0."""

import pytest

from common.errors import EtlErrors
from postgresql.config import build_dsn, require_env


def test_it_l0_cfg_001_require_env_ok(monkeypatch: pytest.MonkeyPatch) -> None:
    """IT-L0-CFG-001: require_env 정상."""
    monkeypatch.setenv("PGUSER", "user")
    assert require_env("PGUSER") == "user"


def test_it_l0_cfg_002_require_env_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    """IT-L0-CFG-002: require_env 누락 시 ValueError."""
    monkeypatch.delenv("PGUSER", raising=False)
    with pytest.raises(ValueError, match="PGUSER"):
        require_env("PGUSER")


def test_it_l0_cfg_003_build_dsn_format(monkeypatch: pytest.MonkeyPatch) -> None:
    """IT-L0-CFG-003: build_dsn URI 형식."""
    monkeypatch.setenv("PGUSER", "user")
    monkeypatch.setenv("PGPASSWORD", "password")
    monkeypatch.setenv("PGHOST", "localhost")
    monkeypatch.setenv("PGPORT", "5432")
    monkeypatch.setenv("PGDATABASE", "service")
    assert build_dsn() == "postgresql://user:password@localhost:5432/service"
