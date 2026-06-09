"""post_analysis 전체 오케스트레이터: get_reviews → analyze_sentimental → analyze_keywords → analyze_it_keywords."""

from __future__ import annotations

import argparse
import logging
from collections.abc import Callable

import common.env  # noqa: F401 — OpenAI·DB 환경변수
from analyze_it_keywords import analyze_it_keywords
from analyze_keywords import analyze_keywords
from analyze_sentimental import analyze_sentimental
from common.errors import PostAnalysisErrors
from get_reviews import get_reviews

logger = logging.getLogger(__name__)


def run_pipeline(
    max_rows: int | None = None,
    it_keywords_max_rows: int | None = None,
    overwrite_it_keywords: bool = False,
    it_keywords_workers: int = 1,
) -> None:
    """한 프로세스에서 1) 적재, 2) 감성 분석, 3) IC01 키워드, 4) IC02 키워드 순으로 실행한다.

    Args:
        max_rows: 기존 IC01 BERT 키워드 추출 상한. ``None``이면 제한 없음.
            ``analyze_keywords(max_rows=...)``에만 전달한다.
        it_keywords_max_rows: IC02 IT 키워드 추출 상한. ``None``이면 제한 없음.
            ``analyze_it_keywords(max_rows=...)``에만 전달한다.
        overwrite_it_keywords: 기존 IC02 keywords 값을 다시 생성할지 여부.
            ``analyze_it_keywords(overwrite=...)``에만 전달한다.

    Raises:
        ValueError: ``max_rows`` 또는 ``it_keywords_max_rows``가 0 이하일 때.
        Exception: 어느 단계에서든 실패 시 해당 예외를 그대로 전파한다.

    Note:
        함수 유형: F — 오케스트레이션
        안전성: Level 2 — 각 단계 DB UPSERT
        불변 규칙: 기존 IC01 3단계 순서 뒤에 IC02 키워드 단계를 추가한다.
    """
    if max_rows is not None and max_rows <= 0:
        raise ValueError(PostAnalysisErrors.Pipeline.invalid_max_rows(max_rows))
    if it_keywords_max_rows is not None and it_keywords_max_rows <= 0:
        raise ValueError(
            PostAnalysisErrors.Pipeline.invalid_max_rows(it_keywords_max_rows)
        )
    if it_keywords_workers <= 0:
        raise ValueError("it_keywords_workers must be greater than 0")

    steps: tuple[tuple[int, str, Callable[..., None], dict], ...] = (
        (1, "get_reviews", get_reviews, {}),
        (2, "analyze_sentimental", analyze_sentimental, {}),
        (3, "analyze_keywords", analyze_keywords, {"max_rows": max_rows}),
        (
            4,
            "analyze_it_keywords",
            analyze_it_keywords,
            {
                "max_rows": it_keywords_max_rows,
                "overwrite": overwrite_it_keywords,
                "workers": it_keywords_workers,
            },
        ),
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
    """CLI 인자를 파싱한다.

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
    parser.add_argument(
        "--it-keywords-max-rows",
        type=int,
        default=None,
        help="IC02 IT 키워드 추출 상한 (미지정 시 제한 없음)",
    )
    parser.add_argument(
        "--overwrite-it-keywords",
        action="store_true",
        help="기존 IC02 keywords를 다시 생성",
    )
    parser.add_argument(
        "--it-keywords-workers",
        type=int,
        default=1,
        help="IC02 IT keyword extraction worker count",
    )
    return parser.parse_args()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s [%(name)s] %(message)s",
    )
    args = _parse_args()
    run_pipeline(
        max_rows=args.max_rows,
        it_keywords_max_rows=args.it_keywords_max_rows,
        overwrite_it_keywords=args.overwrite_it_keywords,
        it_keywords_workers=args.it_keywords_workers,
    )
