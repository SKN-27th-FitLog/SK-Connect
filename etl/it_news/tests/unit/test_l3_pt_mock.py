"""IT-L3-PT: pytorch HTTP mock."""

import json
from unittest.mock import MagicMock, patch

import pandas as pd

from common.constant import CrawlingColumn
from crawling import crawling_thread_pytorch as pt


def test_it_l3_pt_001_get_article_list_mock() -> None:
    """IT-L3-PT-001: Discourse 목록 mock."""
    list_html = """
    <tr class="topic-list-item">
      <td class="main-link"><a class="title" href="/t/slug/1">T</a></td>
    </tr>
    """
    mock_resp = MagicMock()
    mock_resp.text = list_html
    empty_resp = MagicMock()
    empty_resp.text = "<html></html>"

    with patch(
        "crawling.crawling_thread_pytorch.requests.get",
        side_effect=[mock_resp, empty_resp],
    ):
        urls = pt.get_article_list()

    assert any("/t/slug/1" in u for u in urls)


def test_it_l3_pt_002_parse_article_mock() -> None:
    """IT-L3-PT-002: HTML+JSON mock → dict."""
    html = """
    <title>Page</title>
    <div id="topic-title"><h1><a>Topic</a></h1></div>
    <meta name="description" content="Desc body">
    <time class="post-time" datetime="2026-05-20T10:00:00Z"></time>
    """
    json_body = {
        "views": 5,
        "post_stream": {"posts": [{"username": "alice"}]},
    }
    html_resp = MagicMock()
    html_resp.text = html
    json_resp = MagicMock()
    json_resp.json.return_value = json_body
    json_resp.raise_for_status = MagicMock()

    with patch(
        "crawling.crawling_thread_pytorch.requests.get",
        side_effect=[html_resp, json_resp],
    ):
        row = pt.parse_article("https://discuss.pytorch.kr/t/slug/42")

    assert row[CrawlingColumn.TITLE.value] == "Topic"
    assert row[CrawlingColumn.VIEW_COUNT.value] == 5
    assert row[CrawlingColumn.AUTHOR.value] == "alice"


def test_it_l3_pt_003_crawling_thread_delegates() -> None:
    """IT-L3-PT-003: crawling_thread_pytorch → run_crawl_and_save 위임."""
    with (
        patch("crawling.crawling_thread_pytorch.get_article_list", return_value=[]),
        patch("crawling.crawling_thread_pytorch.run_crawl_and_save") as mock_run,
    ):
        mock_run.return_value = (pd.DataFrame(), pd.DataFrame())
        pt.crawling_thread_pytorch()
    mock_run.assert_called_once()
