"""IT-L0-GEEK: crawling_thread_geeknews slicing Level 0."""

from datetime import datetime

import pytest
from bs4 import BeautifulSoup

from common.constant import CrawlingConstant
from common.errors import EtlErrors
from crawling.crawling_thread_geeknews import (
    slicing_comment_count,
    slicing_created_at,
    slicing_thread,
)


def test_it_l0_geek_001_slicing_thread() -> None:
    """IT-L0-GEEK-001: slicing_thread geeknews_ 접두 (INV-03)."""
    url = "https://news.hada.io/topic?id=123"
    assert slicing_thread(url) == "geeknews_123"


def test_it_l0_geek_002_slicing_created_at_raises() -> None:
    """IT-L0-GEEK-002: 작성일 없으면 ValueError."""
    soup = BeautifulSoup('<div class="topicinfo"><span>by user</span></div>', "html.parser")
    with pytest.raises(ValueError, match=EtlErrors.Crawl.created_at_not_found()):
        slicing_created_at(soup)


def test_it_l0_geek_003_slicing_comment_count_default() -> None:
    """IT-L0-GEEK-003: 댓글 수 없으면 0."""
    soup = BeautifulSoup("<div></div>", "html.parser")
    assert slicing_comment_count(soup) == CrawlingConstant.DEFAULT_INT
