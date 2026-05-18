"""Lambda: LLM 키워드 추출 (`analyze_keywords_by_llm`)."""

from __future__ import annotations

import logging
from typing import Any

from common.constant import (
    PostAnalysisLambdaEventKey,
    PostAnalysisLambdaResponseField,
    PostAnalysisLambdaStep,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger("post_analysis_analyze_keywords_by_llm")


def _parse_max_keyword_rows(event: dict) -> int | None:
    """event에서 청크 크기를 읽는다. 없거나 비어 있으면 ``None``(전체)."""
    key = PostAnalysisLambdaEventKey.MAX_KEYWORD_ROWS
    raw = event.get(key)
    if raw is None or raw == "":
        return None
    try:
        n = int(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"{key}는 생략하거나 양의 정수여야 합니다. 받은 값: {raw!r}"
        ) from exc
    if n <= 0:
        raise ValueError(f"{key}는 양의 정수여야 합니다. 받은 값: {n}")
    return n


def lambda_handler(event: dict | None, context: Any) -> dict[str, Any]:
    """AWS Lambda entry point for post_analysis `analyze_keywords_by_llm`.

    event 예시::

        {
            "max_keyword_rows": 20
        }

    - ``max_keyword_rows`` 생략: 필터 후 대상 전체 처리(기존 스크립트와 동일).
    - 양의 정수: 해당 개수만큼만 LLM 처리(타임아웃·청크 실행용).
    """
    if event is None:
        event = {}

    step = PostAnalysisLambdaStep.ANALYZE_KEYWORDS_BY_LLM.value
    rf = PostAnalysisLambdaResponseField

    logger.info(
        "post_analysis analyze_keywords_by_llm event received: keys=%s",
        list(event.keys()),
    )

    try:
        max_rows = _parse_max_keyword_rows(event)
    except ValueError as e:
        logger.warning(str(e))
        return {
            "statusCode": 400,
            "body": {
                rf.STEP: step,
                rf.OK: False,
                rf.ERROR: str(e),
            },
        }

    try:
        from analyze_keywords_by_llm import analyze_keywords_by_llm

        analyze_keywords_by_llm(max_rows=max_rows)

        body: dict[str, Any] = {
            rf.STEP: step,
            rf.OK: True,
        }
        if max_rows is not None:
            body[PostAnalysisLambdaEventKey.MAX_KEYWORD_ROWS] = max_rows

        return {
            "statusCode": 200,
            "body": body,
        }

    except Exception as e:
        logger.error(
            "post_analysis analyze_keywords_by_llm failed: %s",
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
