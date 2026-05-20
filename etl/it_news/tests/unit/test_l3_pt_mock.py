"""IT-L3-PT: pytorch HTTP mock."""

import json
from datetime import datetime
from unittest.mock import MagicMock, patch

import pandas as pd

from common.constant import CrawlingColumn
from crawling import crawling_thread_pytorch as pt


def _list_json_response(topics: list[dict]) -> MagicMock:
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    resp.json.return_value = {"topic_list": {"topics": topics}}
    return resp


def test_it_l3_pt_001_get_article_list_watermark_filter() -> None:
    """IT-L3-PT-001: 목록 JSON mock — 워터마크 통과 URL만, 조기 종료."""
    topics_page0 = [
        {
            "id": 1,
            "slug": "new",
            "created_at": "2026-05-20T10:00:00.000Z",
            "pinned": False,
        },
        {
            "id": 2,
            "slug": "old",
            "created_at": "2020-01-01T00:00:00.000Z",
            "pinned": False,
        },
        {
            "id": 99,
            "slug": "pinned-old",
            "created_at": "2019-01-01T00:00:00.000Z",
            "pinned": True,
        },
    ]
    # page 1 would be fetched only if page 0 had a new topic — it does not call page 1
    # because page_has_new is True from id=1; add page 1 all old to verify stop after page 1
    topics_page1 = [
        {
            "id": 3,
            "slug": "older",
            "created_at": "2019-06-01T00:00:00.000Z",
            "pinned": False,
        },
    ]
    empty_topics = []

    with patch(
        "crawling.crawling_thread_pytorch.requests.get",
        side_effect=[
            _list_json_response(topics_page0),
            _list_json_response(topics_page1),
            _list_json_response(empty_topics),
        ],
    ) as mock_get:
        urls = pt.get_article_list(last_created_at=datetime(2026, 5, 19, 0, 0, 0))

    assert len(urls) == 1
    assert "/t/new/1" in urls[0]
    assert mock_get.call_count == 2


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
    threshold = datetime(2026, 5, 1)
    with (
        patch("crawling.crawling_thread_pytorch.get_article_list", return_value=[]) as mock_list,
        patch("crawling.crawling_thread_pytorch.run_crawl_and_save") as mock_run,
    ):
        mock_run.return_value = (pd.DataFrame(), pd.DataFrame())
        pt.crawling_thread_pytorch(last_created_at=threshold)
    mock_list.assert_called_once_with(last_created_at=threshold)
    mock_run.assert_called_once()


def test_it_l3_pt_004_early_stop_when_page_all_old() -> None:
    """IT-L3-PT-004: 비고정 토픽이 모두 워터마크 이하이면 다음 페이지 미요청."""
    old_only = [
        {
            "id": 10,
            "slug": "x",
            "created_at": "2020-01-01T00:00:00.000Z",
            "pinned": False,
        },
    ]
    with patch(
        "crawling.crawling_thread_pytorch.requests.get",
        return_value=_list_json_response(old_only),
    ) as mock_get:
        urls = pt.get_article_list(last_created_at=datetime(2026, 5, 19))
    assert urls == []
    assert mock_get.call_count == 1
