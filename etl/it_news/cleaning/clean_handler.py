from __future__ import annotations

import argparse
import asyncio
import logging
from typing import Any

from common.constant import ItNewsLambdaDefaults, ItNewsLambdaEventKey
from cleaning.clean_service import CleanService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger("it_news_clean")


def lambda_handler(event: dict | None, context: Any) -> dict[str, Any]:
    """AWS Lambda entry point for IT news cleaning.

    event 예시:
    {
        ItNewsLambdaEventKey.OUTPUT_CSV_PREFIX: "<prefix>"
    }
    """

    if event is None:
        event = {}

    output_csv_prefix = event.get(
        ItNewsLambdaEventKey.OUTPUT_CSV_PREFIX,
        ItNewsLambdaDefaults.OUTPUT_CSV_PREFIX,
    )

    logger.info(
        "IT news clean event received: output_csv_prefix=%s",
        output_csv_prefix,
    )

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        result = loop.run_until_complete(
            CleanService.run_clean(
                output_csv_prefix=output_csv_prefix,
            )
        )

        return {
            "statusCode": 200,
            "body": result,
        }

    except Exception as e:
        logger.error(
            "IT news clean failed: %s",
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
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-csv-prefix",
        type=str,
        default=ItNewsLambdaDefaults.OUTPUT_CSV_PREFIX,
        help="Output CSV prefix for cleaning result",
    )
    args = parser.parse_args()

    response = lambda_handler(
        {
            ItNewsLambdaEventKey.OUTPUT_CSV_PREFIX: args.output_csv_prefix,
        },
        None,
    )

    logger.info("Local execution result: %s", response)