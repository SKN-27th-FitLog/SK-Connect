from __future__ import annotations

import asyncio
import logging
from typing import Any

from common.constant import CrawlSourceToken, Service
from common.utils import get_last_success_date, get_run_time
from crawling.crawling_thread_geeknews import crawling_thread_geeknews
from crawling.crawling_thread_pytorch import crawling_thread_pytorch

logger = logging.getLogger(__name__)

_ALLOWED_CRAWL_SOURCES = frozenset(
    {
        CrawlSourceToken.ALL,
        Service.GEEKNEWS.service,
        Service.PYTORCH.service,
    }
)


class CrawlService:
    """IT 뉴스 크롤링 실행 서비스.

    기존 동기 크롤링 함수를 Lambda/async handler에서 호출할 수 있도록 래핑한다.
    """

    @staticmethod
    async def run_crawl(source: str = CrawlSourceToken.ALL) -> dict[str, Any]:
        """크롤링 실행.

        Parameters
        ----------
        source:
            ``CrawlSourceToken.ALL`` 또는 ``Service`` 슬러그(geeknews/pytorch).
            기본값은 전체 실행이다.
        """

        normalized_source = source.lower().strip()
        if normalized_source not in _ALLOWED_CRAWL_SOURCES:
            allowed = ", ".join(sorted(_ALLOWED_CRAWL_SOURCES))
            raise ValueError(f"Invalid source. Allowed values are: {allowed}")

        run_time = get_run_time()

        result: dict[str, Any] = {}
        geek_slug = Service.GEEKNEWS.service
        pytorch_slug = Service.PYTORCH.service

        if normalized_source in (CrawlSourceToken.ALL, geek_slug):
            logger.info("크롤링 시작: %s", geek_slug)

            last_geek = get_last_success_date(Service.GEEKNEWS)
            g_ok, g_fail = await asyncio.to_thread(
                crawling_thread_geeknews,
                run_time=run_time,
                last_created_at=last_geek,
            )

            result[geek_slug] = {
                "success_count": len(g_ok),
                "fail_count": len(g_fail),
            }

            logger.info(
                "크롤링 종료: %s success=%d fail=%d",
                geek_slug,
                len(g_ok),
                len(g_fail),
            )

        if normalized_source in (CrawlSourceToken.ALL, pytorch_slug):
            logger.info("크롤링 시작: %s", pytorch_slug)

            last_pt = get_last_success_date(Service.PYTORCH)
            p_ok, p_fail = await asyncio.to_thread(
                crawling_thread_pytorch,
                run_time=run_time,
                last_created_at=last_pt,
            )

            result[pytorch_slug] = {
                "success_count": len(p_ok),
                "fail_count": len(p_fail),
            }

            logger.info(
                "크롤링 종료: %s success=%d fail=%d",
                pytorch_slug,
                len(p_ok),
                len(p_fail),
            )

        return {
            "step": "crawl",
            "source": normalized_source,
            "result": result,
        }