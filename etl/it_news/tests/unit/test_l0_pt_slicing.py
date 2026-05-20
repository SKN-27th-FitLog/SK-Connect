"""IT-L0-PT: crawling_thread_pytorch slicing Level 0."""

from datetime import datetime

from bs4 import BeautifulSoup

from crawling.crawling_thread_pytorch import slicing_created_at, slicing_thread


def test_it_l0_pt_001_slicing_thread() -> None:
    """IT-L0-PT-001: slicing_thread pytorch_ 접두."""
    url = "https://discuss.pytorch.kr/t/slug/999"
    assert slicing_thread(url) == "pytorch_999"


def test_it_l0_pt_002_slicing_created_at_iso() -> None:
    """IT-L0-PT-002: ISO datetime 파싱."""
    html = '<time class="post-time" datetime="2026-05-20T10:00:00Z"></time>'
    soup = BeautifulSoup(html, "html.parser")
    result = slicing_created_at(soup)
    assert result == datetime(2026, 5, 20, 10, 0, 0)
