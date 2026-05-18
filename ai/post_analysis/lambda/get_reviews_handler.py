"""Lambda: `crawling` 신규 → `analysis` 적재 (`get_reviews`)."""

from __future__ import annotations

import logging
from typing import Any

from common.constant import (
    PostAnalysisLambdaResponseField,
    PostAnalysisLambdaStep,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger("post_analysis_get_reviews")


def lambda_handler(event: dict | None, context: Any) -> dict[str, Any]:
    """AWS Lambda entry point for post_analysis `get_reviews`.

    event:
        현재 옵션 없음. 향후 확장용 dict.
    """
    if event is None:
        event = {}

    step = PostAnalysisLambdaStep.GET_REVIEWS.value
    rf = PostAnalysisLambdaResponseField

    logger.info("post_analysis get_reviews event received: keys=%s", list(event.keys()))

    try:
        from get_reviews import get_reviews

        get_reviews()

        return {
            "statusCode": 200,
            "body": {
                rf.STEP: step,
                rf.OK: True,
            },
        }

    except Exception as e:
        logger.error("post_analysis get_reviews failed: %s", str(e), exc_info=True)

        return {
            "statusCode": 500,
            "body": {
                rf.STEP: step,
                rf.OK: False,
                rf.ERROR: str(e),
            },
        }


if __name__ == "__main__":
    _r = lambda_handler({}, None)
    logger.info("Local execution result: %s", _r)
