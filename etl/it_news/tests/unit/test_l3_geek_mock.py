"""IT-L3-GEEK: geeknews HTTP mock."""

from unittest.mock import MagicMock, patch

import pandas as pd

from common.constant import CrawlingColumn
from crawling import crawling_thread_geeknews as geek


def test_it_l3_geek_001_get_article_list_mock() -> None:
    """IT-L3-GEEK-001: 목록 HTML mock → URL 수집."""
    list_html = """
    <div class="topic_row">
      <div class="topicdesc"><a href="topic?id=1">t</a></div>
    </div>
    """
    mock_resp = MagicMock()
    mock_resp.text = list_html
    empty_resp = MagicMock()
    empty_resp.text = "<html></html>"

    with patch(
        "crawling.crawling_thread_geeknews.requests.get",
        side_effect=[mock_resp, empty_resp],
    ):
        urls = geek.get_article_list()

    assert any("topic?id=1" in u for u in urls)


def test_it_l3_geek_002_parse_article_mock() -> None:
    """IT-L3-GEEK-002: 토픽 HTML mock → dict 키."""
    topic_html = """
    <div class="topic"><div class="topictitle"><h1>Title</h1></div></div>
    <div id="topic_contents">Body text</div>
    <div class="topicinfo">
      <span>3시간전</span>
      <span id="tp10">10</span>
      <a href="/@author">a</a>
    </div>
    """
    mock_resp = MagicMock()
    mock_resp.text = topic_html

    with patch("crawling.crawling_thread_geeknews.requests.get", return_value=mock_resp):
        row = geek.parse_article("https://news.hada.io/topic?id=99")

    assert row[CrawlingColumn.TITLE.value] == "Title"
    assert row[CrawlingColumn.THREAD.value] == "geeknews_99"


def test_it_l3_geek_003_crawling_thread_delegates() -> None:
    """IT-L3-GEEK-003: crawling_thread_geeknews → run_crawl_and_save 위임."""
    with (
        patch("crawling.crawling_thread_geeknews.get_article_list", return_value=[]),
        patch("crawling.crawling_thread_geeknews.run_crawl_and_save") as mock_run,
    ):
        mock_run.return_value = (pd.DataFrame(), pd.DataFrame())
        geek.crawling_thread_geeknews()
    mock_run.assert_called_once()
