"""IT-L0-ERR / IT-L0-CST: errors·constant Level 0."""

import pytest

from common.constant import (
    CodeTable,
    CrawlingConstant,
    InformationCdCode,
    Service,
    Stage,
    Status,
)
from common.errors import EtlErrors


def test_it_l0_err_001_messages_non_empty() -> None:
    """IT-L0-ERR-001: EtlErrors 메시지 non-empty."""
    assert EtlErrors.Crawl.created_at_not_found()
    assert EtlErrors.Save.merge_insert_failed()
    assert EtlErrors.Db.missing_env_var("PGUSER")


def test_it_l0_err_002_unsupported_service_format() -> None:
    """IT-L0-ERR-002: unsupported_service에 받은 값 포함."""
    msg = EtlErrors.Watermark.unsupported_service("bad")
    assert "bad" in msg


def test_it_l0_cst_001_service_url_and_name() -> None:
    """IT-L0-CST-001: Service URL·service 속성."""
    assert "hada.io" in Service.GEEKNEWS.url
    assert Service.GEEKNEWS.service == "geeknews"
    assert Service.PYTORCH.service == "pytorch"


def test_it_l0_cst_002_stage_values() -> None:
    """IT-L0-CST-002: Stage 값 (INV-02)."""
    assert Stage.CRAWLING.value == "raw"
    assert Stage.CLEANING.value == "cleaning"
    assert Stage.SAVE.value == "save"


def test_it_l0_cst_003_code_table_it_etc() -> None:
    """IT-L0-CST-003: CodeTable IC02·CA07 (INV-07)."""
    assert CodeTable.INFORMATION_IT.value == InformationCdCode.IT_INFO.value
    assert CodeTable.CATEGORY_ETC.value == "CA07"


def test_it_l0_cst_004_lookback_days() -> None:
    """IT-L0-CST-004: ETL_CRAWL_LOOKBACK_DAYS."""
    assert CrawlingConstant.ETL_CRAWL_LOOKBACK_DAYS == 90
