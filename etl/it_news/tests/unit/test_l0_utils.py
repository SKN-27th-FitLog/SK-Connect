"""IT-L0-UTIL: common.utils Level 0."""

from datetime import date, datetime, timedelta

import pandas as pd
import pytest

from common.constant import CodeTable, CrawlingColumn, CrawlingConstant, Service, Stage, Status
from common.crawling_http import user_agent_headers
from common.utils import (
    build_csv_path,
    coalesce_last_created_at,
    default_last_collected_at,
    format_hhmmss,
    information_cd_for_path,
    korean_relative_time,
    parse_segment_int,
)


def test_it_l0_util_001_format_hhmmss() -> None:
    """IT-L0-UTIL-001: format_hhmmss 정상."""
    assert format_hhmmss(datetime(2026, 4, 21, 12, 52, 1)) == "125201"


def test_it_l0_util_002_parse_segment_int() -> None:
    """IT-L0-UTIL-002: parse_segment_int 정상·실패."""
    assert parse_segment_int("year=2026", "year") == 2026
    assert parse_segment_int("year=abc", "year") is None
    assert parse_segment_int("month=04", "month") == 4


def test_it_l0_util_003_build_csv_path_inv01(fixed_now: datetime) -> None:
    """IT-L0-UTIL-003: build_csv_path 세그먼트 불변 (INV-01)."""
    path = build_csv_path(
        Stage.CRAWLING,
        CodeTable.INFORMATION_IT.value,
        Service.GEEKNEWS.service,
        Status.SUCCESS,
        fixed_now,
    )
    parts = path.as_posix().split("/")
    assert parts[-1] == "geeknews_113045.csv"
    assert "process=raw" in parts
    assert "information_cd=IC02" in parts
    assert "year=2026" in parts
    assert "month=05" in parts
    assert "day=20" in parts
    assert "status=success" in parts


def test_it_l0_util_004_information_cd_for_path() -> None:
    """IT-L0-UTIL-004: information_cd_for_path 기본·mode."""
    assert information_cd_for_path(pd.DataFrame()) == CodeTable.INFORMATION_IT.value
    df = pd.DataFrame({CrawlingColumn.INFORMATION_CD.value: ["IC02", "IC02"]})
    assert information_cd_for_path(df) == "IC02"


def test_it_l0_util_005_korean_relative_time() -> None:
    """IT-L0-UTIL-005: korean_relative_time 정상·경계."""
    now = datetime(2026, 5, 20, 12, 0, 0)
    assert korean_relative_time("3시간전", now=now) == now - timedelta(hours=3)
    assert korean_relative_time("방금", now=now) == now
    assert korean_relative_time("알수없음", now=now) is None
    assert korean_relative_time("", now=now) is None


def test_it_l0_util_006_coalesce_last_created_at() -> None:
    """IT-L0-UTIL-006: coalesce_last_created_at None·NaT·유효."""
    default = default_last_collected_at()
    assert coalesce_last_created_at(None) == default
    assert coalesce_last_created_at(float("nan")) == default
    dt = datetime(2026, 1, 1, 0, 0, 0)
    assert coalesce_last_created_at(dt) == dt


def test_it_l0_util_007_default_last_collected_at() -> None:
    """IT-L0-UTIL-007: default_last_collected_at 90일 lookback (INV-08)."""
    expected_date = date.today() - timedelta(days=CrawlingConstant.ETL_CRAWL_LOOKBACK_DAYS)
    result = default_last_collected_at()
    assert result.date() == expected_date
    assert result.hour == 0 and result.minute == 0


def test_it_l0_util_008_user_agent_headers() -> None:
    """IT-L0-UTIL-008: user_agent_headers 키·값."""
    headers = user_agent_headers()
    assert headers[CrawlingConstant.USER_AGENT_HEADER] == CrawlingConstant.USER_AGENT
