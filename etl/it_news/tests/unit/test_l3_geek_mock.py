"""IT-L3-GEEK: geeknews HTTP mock."""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pandas as pd

from common.constant import CrawlingColumn
from common.utils import extract_korean_relative_time_from_text
from crawling import crawling_thread_geeknews as geek

_FIXED_NOW = datetime(2026, 5, 20, 12, 0, 0)


def _extract_at_fixed_now(text: str, now=None):
    return extract_korean_relative_time_from_text(text, now=_FIXED_NOW)


def _list_html(rows: str) -> str:
    return f"<html><body>{rows}</body></html>"


def test_it_l3_geek_001_get_article_list_watermark_filter() -> None:
    """IT-L3-GEEK-001: 목록 HTML mock — 워터마크 통과 URL만, 조기 종료."""
    page1 = _list_html(
        """
    <div class="topic_row">
      <div class="topicdesc"><a href="topic?id=1">new</a></div>
      <div class="topicinfo">3 points by u 1시간전 | 댓글</div>
    </div>
    <div class="topic_row">
      <div class="topicdesc"><a href="topic?id=2">old</a></div>
      <div class="topicinfo">1 points by u 30일전 | 댓글</div>
    </div>
    """
    )
    page2 = _list_html(
        """
    <div class="topic_row">
      <div class="topicdesc"><a href="topic?id=3">older</a></div>
      <div class="topicinfo">0 points by u 60일전 | 댓글</div>
    </div>
    """
    )
    mock_p1 = MagicMock()
    mock_p1.text = page1
    mock_p2 = MagicMock()
    mock_p2.text = page2

    with (
        patch(
            "crawling.crawling_thread_geeknews.requests.get",
            side_effect=[mock_p1, mock_p2],
        ) as mock_get,
        patch(
            "crawling.crawling_thread_geeknews.extract_korean_relative_time_from_text",
            side_effect=_extract_at_fixed_now,
        ),
    ):
        urls = geek.get_article_list(last_created_at=datetime(2026, 5, 19, 0, 0, 0))

    assert len(urls) == 1
    assert "topic?id=1" in urls[0]
    assert mock_get.call_count == 2


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
    threshold = datetime(2026, 5, 1)
    with (
        patch("crawling.crawling_thread_geeknews.get_article_list", return_value=[]) as mock_list,
        patch("crawling.crawling_thread_geeknews.run_crawl_and_save") as mock_run,
    ):
        mock_run.return_value = (pd.DataFrame(), pd.DataFrame())
        geek.crawling_thread_geeknews(last_created_at=threshold)
    mock_list.assert_called_once_with(last_created_at=threshold)
    mock_run.assert_called_once()


def test_it_l3_geek_004_early_stop_when_page_all_old() -> None:
    """IT-L3-GEEK-004: 페이지 전체가 워터마크 이하이면 다음 페이지 미요청."""
    old_page = _list_html(
        """
    <div class="topic_row">
      <div class="topicdesc"><a href="topic?id=9">old</a></div>
      <div class="topicinfo">1 points by u 90일전 | 댓글</div>
    </div>
    """
    )
    mock_resp = MagicMock()
    mock_resp.text = old_page

    with (
        patch("crawling.crawling_thread_geeknews.requests.get", return_value=mock_resp) as mock_get,
        patch(
            "crawling.crawling_thread_geeknews.extract_korean_relative_time_from_text",
            side_effect=_extract_at_fixed_now,
        ),
    ):
        urls = geek.get_article_list(last_created_at=datetime(2026, 5, 19))

    assert urls == []
    assert mock_get.call_count == 1
