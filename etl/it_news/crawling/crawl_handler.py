from __future__ import annotations

import argparse
import asyncio
import logging
from typing import Any

from common.constant import (
    CrawlSourceToken,
    ItNewsLambdaDefaults,
    ItNewsLambdaEventKey,
    Service,
)
from crawling.crawl_service import CrawlService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger("it_news_crawl")


def lambda_handler(event: dict | None, context: Any) -> dict[str, Any]:
    """AWS Lambda entry point for IT news crawling.

    event 예시:
    {
        ItNewsLambdaEventKey.SOURCE: CrawlSourceToken.ALL
    }

    source 값:
    - CrawlSourceToken.ALL (전체)
    - Service 슬러그: geeknews, pytorch
    """

    if event is None:
        event = {}

    source = event.get(ItNewsLambdaEventKey.SOURCE, ItNewsLambdaDefaults.SOURCE)

    logger.info("IT news crawl event received: source=%s", source)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        result = loop.run_until_complete(
            CrawlService.run_crawl(source=source)
        )

        return {
            "statusCode": 200,
            "body": result,
        }

    except Exception as e:
        logger.error(
            "IT news crawl failed: %s",
            str(e),
            exc_info=True,
        )

        return {
            "statusCode": 500,
            "body": {
                "error": str(e),
            },
        }

    finally:
        loop.close()


if __name__ == "__main__":
    _CRAWL_CLI_CHOICES = [
        CrawlSourceToken.ALL,
        Service.GEEKNEWS.service,
        Service.PYTORCH.service,
    ]
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--source",
        type=str,
        default=ItNewsLambdaDefaults.SOURCE,
        choices=_CRAWL_CLI_CHOICES,
        help="Target source: all, geeknews, pytorch",
    )
    args = parser.parse_args()

    response = lambda_handler(
        {
            ItNewsLambdaEventKey.SOURCE: args.source,
        },
        None,
    )

    logger.info("Local execution result: %s", response)