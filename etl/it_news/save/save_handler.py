from __future__ import annotations

import argparse
import asyncio
import logging
from typing import Any

from common.constant import ItNewsLambdaDefaults, ItNewsLambdaEventKey
from save.save_service import SaveService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger("it_news_save")


def lambda_handler(event: dict | None, context: Any) -> dict[str, Any]:
    """AWS Lambda entry point for IT news save.

    event 예시:
    {
        ItNewsLambdaEventKey.SAVE_FILE_PREFIX: "<prefix>"
    }
    """

    if event is None:
        event = {}

    save_file_prefix = event.get(
        ItNewsLambdaEventKey.SAVE_FILE_PREFIX,
        ItNewsLambdaDefaults.SAVE_FILE_PREFIX,
    )

    logger.info(
        "IT news save event received: save_file_prefix=%s",
        save_file_prefix,
    )

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        result = loop.run_until_complete(
            SaveService.run_save(
                save_file_prefix=save_file_prefix,
            )
        )

        return {
            "statusCode": 200,
            "body": result,
        }

    except Exception as e:
        logger.error(
            "IT news save failed: %s",
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
        "--save-file-prefix",
        type=str,
        default=ItNewsLambdaDefaults.SAVE_FILE_PREFIX,
        help="Output CSV prefix for save result",
    )
    args = parser.parse_args()

    response = lambda_handler(
        {
            ItNewsLambdaEventKey.SAVE_FILE_PREFIX: args.save_file_prefix,
        },
        None,
    )

    logger.info("Local execution result: %s", response)