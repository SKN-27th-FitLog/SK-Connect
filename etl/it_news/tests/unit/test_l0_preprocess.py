"""IT-L0-PRE: common.preprocess Level 0."""

import pandas as pd
import pytest

from common.constant import CodeTable, CrawlingColumn, Status
from common.preprocess import (
    cleaning_continuous_newlines,
    cleaning_continuous_spaces,
    cleaning_data_in_df,
    cleaning_special_characters,
    separate_success_and_fail,
    wrap_article_url_as_html_anchor,
)


def _df_with_state(rows: list[dict]) -> pd.DataFrame:
    c = CrawlingColumn
    out = pd.DataFrame(rows)
    if c.STATE.value not in out.columns:
        out[c.STATE.value] = Status.SUCCESS.value
    return out


def test_it_l0_pre_001_separate_success_and_fail() -> None:
    """IT-L0-PRE-001: state로 success/fail 분리·state 제거."""
    c = CrawlingColumn
    df = pd.DataFrame(
        [
            {c.STATE.value: Status.SUCCESS.value, c.TITLE.value: "a"},
            {c.STATE.value: Status.FAIL.value, c.TITLE.value: "b"},
        ]
    )
    ok, fail = separate_success_and_fail(df)
    assert len(ok) == 1 and c.STATE.value not in ok.columns
    assert len(fail) == 1 and c.STATE.value not in fail.columns


def test_it_l0_pre_002_cleaning_special_characters() -> None:
    """IT-L0-PRE-002: ZW·NBSP 제거."""
    c = CrawlingColumn
    df = pd.DataFrame(
        {c.TITLE.value: ["a\u200bb"], c.CONTENT.value: ["x\u00a0y"]}
    )
    out = cleaning_special_characters(df)
    assert "\u200b" not in str(out[c.TITLE.value].iloc[0])
    assert "\u00a0" not in str(out[c.CONTENT.value].iloc[0])


def test_it_l0_pre_003_cleaning_continuous_newlines() -> None:
    """IT-L0-PRE-003: 연속 줄바꿈 축소."""
    c = CrawlingColumn
    df = pd.DataFrame({c.CONTENT.value: ["a\n\n\nb"]})
    out = cleaning_continuous_newlines(df)
    assert out[c.CONTENT.value].iloc[0] == "a\nb"


def test_it_l0_pre_004_cleaning_continuous_spaces() -> None:
    """IT-L0-PRE-004: 연속 공백 축소."""
    c = CrawlingColumn
    df = pd.DataFrame({c.TITLE.value: ["a  \t  b"]})
    out = cleaning_continuous_spaces(df)
    assert out[c.TITLE.value].iloc[0] == "a b"


def test_it_l0_pre_005_wrap_article_url_as_html_anchor() -> None:
    """IT-L0-PRE-005: article_url HTML 앵커 (경계)."""
    c = CrawlingColumn
    df = pd.DataFrame(
        {
            c.TITLE.value: ["짧은제목"],
            c.ARTICLE_URL.value: ["https://example.com/path"],
        }
    )
    out = wrap_article_url_as_html_anchor(df)
    cell = out[c.ARTICLE_URL.value].iloc[0]
    assert cell.startswith('<a href="https://example.com/path">')
    assert "짧은제목" in cell
    assert len(cell) <= 500


def test_it_l0_pre_006_cleaning_data_missing_title_fail(minimal_crawl_row: dict) -> None:
    """IT-L0-PRE-006: title 결측 → state=fail (INV-05)."""
    c = CrawlingColumn
    row = {**minimal_crawl_row, c.TITLE.value: None}
    out = cleaning_data_in_df(pd.DataFrame([row]))
    assert (out[c.STATE.value] == Status.FAIL.value).all()


def test_it_l0_pre_007_cleaning_data_duplicate_thread(minimal_crawl_row: dict) -> None:
    """IT-L0-PRE-007: thread 중복 시 last만 유지."""
    c = CrawlingColumn
    r1 = {**minimal_crawl_row, c.TITLE.value: "first"}
    r2 = {**minimal_crawl_row, c.TITLE.value: "second"}
    out = cleaning_data_in_df(pd.DataFrame([r1, r2]))
    success = out[out[c.STATE.value] == Status.SUCCESS.value]
    assert len(success) == 1
    assert success[c.TITLE.value].iloc[0] == "second"


def test_it_l0_pre_008_cleaning_data_success_row(minimal_crawl_row: dict) -> None:
    """IT-L0-PRE-008: 필수 컬럼 채움 → success."""
    c = CrawlingColumn
    out = cleaning_data_in_df(pd.DataFrame([minimal_crawl_row]))
    assert (out[c.STATE.value] == Status.SUCCESS.value).all()


def test_it_l0_pre_009_cleaning_data_mixed_created_at(minimal_crawl_row: dict) -> None:
    """IT-L0-PRE-009: 혼합 datetime 문자열 파싱."""
    c = CrawlingColumn
    r1 = {**minimal_crawl_row, c.CREATED_AT.value: "2026-05-20 10:00:00"}
    r2 = {
        **minimal_crawl_row,
        c.THREAD.value: "pytorch_2",
        c.CREATED_AT.value: "2026-05-20T10:00:00",
    }
    out = cleaning_data_in_df(pd.DataFrame([r1, r2]))
    assert (out[c.STATE.value] == Status.SUCCESS.value).all()


def test_it_l0_pre_010_separate_empty_df() -> None:
    """IT-L0-PRE-010: 빈 DataFrame 분리."""
    c = CrawlingColumn
    df = pd.DataFrame(columns=[c.STATE.value, c.TITLE.value])
    ok, fail = separate_success_and_fail(df)
    assert ok.empty and fail.empty
