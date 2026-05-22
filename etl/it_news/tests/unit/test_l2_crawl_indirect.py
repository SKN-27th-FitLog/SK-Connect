"""IT-L2-CRAWL: run_crawl_and_save 간접."""

from datetime import datetime
from unittest.mock import patch

import pandas as pd
import pytest

from common.constant import CrawlingColumn, Service
from common.crawling_http import run_crawl_and_save


def test_it_l2_crawl_001_parse_failure_becomes_fail_row() -> None:
    """IT-L2-CRAWL-001: parse 예외 → fail row."""

    def boom(_url: str) -> dict:
        raise ValueError("parse fail")

    ok, fail = run_crawl_and_save(
        service=Service.GEEKNEWS,
        article_urls=["http://example.com/a"],
        parse_article=boom,
        tqdm_desc="test",
        last_created_at=datetime(2000, 1, 1),
    )
    assert ok.empty
    assert len(fail) == 1
    assert fail[CrawlingColumn.ERROR.value].iloc[0] == "parse fail"


def test_it_l2_crawl_002_watermark_filters_success() -> None:
    """IT-L2-CRAWL-002: created_at <= threshold 제외."""
    c = CrawlingColumn
    threshold = datetime(2026, 5, 20, 10, 0, 0)

    def parse(_url: str) -> dict:
        return {
            c.TITLE.value: "t",
            c.CONTENT.value: "c",
            c.THREAD.value: "geeknews_1",
            c.ARTICLE_URL.value: _url,
            c.CREATED_AT.value: datetime(2026, 5, 20, 9, 0, 0),
        }

    with patch("common.crawling_http.save_csv"):
        ok, fail = run_crawl_and_save(
            service=Service.GEEKNEWS,
            article_urls=["http://example.com/old"],
            parse_article=parse,
            tqdm_desc="test",
            last_created_at=threshold,
        )
    assert ok.empty and fail.empty


def test_it_l2_crawl_003_saves_csv_when_rows(tmp_path, monkeypatch) -> None:
    """IT-L2-CRAWL-003: success·fail 시 save_csv 호출."""
    c = CrawlingColumn
    saved: list = []

    def capture_save(df, path):  # noqa: ANN001
        saved.append((len(df), str(path)))
        return path

    def parse(url: str) -> dict:
        return {
            c.TITLE.value: "t",
            c.CONTENT.value: "c",
            c.THREAD.value: "geeknews_1",
            c.ARTICLE_URL.value: url,
            c.CREATED_AT.value: datetime(2026, 5, 21, 12, 0, 0),
        }

    monkeypatch.chdir(tmp_path)
    with patch("common.crawling_http.save_csv", side_effect=capture_save):
        run_crawl_and_save(
            service=Service.GEEKNEWS,
            article_urls=["http://example.com/ok"],
            parse_article=parse,
            tqdm_desc="test",
            run_time=datetime(2026, 5, 20, 12, 0, 0),
            last_created_at=datetime(2026, 5, 20, 0, 0, 0),
        )
    assert len(saved) >= 1
