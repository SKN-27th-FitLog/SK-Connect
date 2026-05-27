"""post_analysis 전체 오케스트레이터: get_reviews → analyze_sentimental → analyze_keywords."""

from __future__ import annotations

import argparse
import logging
from collections.abc import Callable

import common.env  # noqa: F401 — OpenAI·DB 환경변수
from analyze_keywords import analyze_keywords
from analyze_sentimental import analyze_sentimental
from common.errors import PostAnalysisErrors
from get_reviews import get_reviews

logger = logging.getLogger(__name__)


def run_pipeline(max_rows: int | None = None) -> None:
    """한 프로세스에서 1) 적재, 2) 감성 분석, 3) BERT 키워드 추출 순으로 실행한다.

    Args:
        max_rows: 3단계 키워드 추출 상한. ``None``이면 제한 없음.
            ``analyze_keywords(max_rows=...)``에 그대로 전달한다.

    Raises:
        ValueError: ``max_rows``가 0 이하일 때.
        Exception: 어느 단계에서든 실패 시 해당 예외를 그대로 전파한다.

    Note:
        함수 유형: F — 오케스트레이션
        안전성: Level 2 — 1~3단계 DB UPSERT
        불변 규칙: ``get_reviews`` → ``analyze_sentimental`` → ``analyze_keywords`` 순서 고정
    """
    if max_rows is not None and max_rows <= 0:
        raise ValueError(PostAnalysisErrors.Pipeline.invalid_max_rows(max_rows))

    steps: tuple[tuple[int, str, Callable[..., None], dict], ...] = (
        (1, "get_reviews", get_reviews, {}),
        (2, "analyze_sentimental", analyze_sentimental, {}),
        (3, "analyze_keywords", analyze_keywords, {"max_rows": max_rows}),
    )
    total = len(steps)

    for step, name, func, kwargs in steps:
        logger.info(PostAnalysisErrors.Pipeline.step_start(step, total, name))
        try:
            func(**kwargs)
        except Exception as exc:
            logger.error(
                PostAnalysisErrors.Pipeline.step_failed(step, total, name, exc)
            )
            raise

    logger.info(PostAnalysisErrors.Pipeline.completed())


def _parse_args() -> argparse.Namespace:
    """CLI 인자(``--max-rows``)를 파싱한다.

    Note:
        함수 유형: C — 입력 검증 (argparse)
        안전성: Level 0 — 외부 상태 변경 없음
    """
    parser = argparse.ArgumentParser(description="post_analysis 전체 파이프라인 실행")
    parser.add_argument(
        "--max-rows",
        type=int,
        default=None,
        help="3단계 키워드 추출 상한 (미지정 시 제한 없음)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s [%(name)s] %(message)s",
    )
    args = _parse_args()
    run_pipeline(max_rows=args.max_rows)
