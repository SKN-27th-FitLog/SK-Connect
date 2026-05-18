"""Lambda: `analysis` 감성·점수 채움 (`analyze_sentimental`)."""

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

logger = logging.getLogger("post_analysis_analyze_sentimental")


def lambda_handler(event: dict | None, context: Any) -> dict[str, Any]:
    """AWS Lambda entry point for post_analysis `analyze_sentimental`.

    event:
        현재 옵션 없음. 향후 확장용 dict.
    """
    if event is None:
        event = {}

    step = PostAnalysisLambdaStep.ANALYZE_SENTIMENTAL.value
    rf = PostAnalysisLambdaResponseField

    logger.info(
        "post_analysis analyze_sentimental event received: keys=%s",
        list(event.keys()),
    )

    try:
        from analyze_sentimental import analyze_sentimental

        analyze_sentimental()

        return {
            "statusCode": 200,
            "body": {
                rf.STEP: step,
                rf.OK: True,
            },
        }

    except Exception as e:
        logger.error(
            "post_analysis analyze_sentimental failed: %s",
            str(e),
            exc_info=True,
        )

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
