"""IC02 IT 뉴스 전용 회사/분류 키워드와 제목 감성을 저장한다."""

from __future__ import annotations

from dataclasses import dataclass
import logging
import re

import pandas as pd

import common.env  # noqa: F401 - DB 환경변수 로드
from common.bert_tokenizer import BertTokenizer
from common.constant import (
    AnalysisColumn,
    AnalyzeItKeywordsConfig,
    CodeTable,
    SentimentResultKey,
)
from common.errors import PostAnalysisErrors
from common.it_company_registry import build_company_keyword_values, match_it_companies
from postgresql.run_query import get_it_keyword_target_data, merge_analysis_data

logger = logging.getLogger(__name__)

_DEPENDENCY_LOGGER_NAMES = (
    "httpx",
    "httpcore",
    "huggingface_hub",
    "transformers",
)


def _configure_cli_logging() -> None:
    """CLI 실행 시 외부 의존성의 정상 INFO 로그 노출을 줄인다."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s [%(name)s] %(message)s")
    for logger_name in _DEPENDENCY_LOGGER_NAMES:
        logging.getLogger(logger_name).setLevel(logging.WARNING)


@dataclass(frozen=True)
class ItKeywordAnalysisResult:
    """IC02 회사 키워드와 제목 감성 처리 결과."""

    keywords: str | None
    sentimental: str
    score: float


def _text_or_empty(value: object) -> str:
    """결측값을 빈 문자열로 바꾸고 나머지는 문자열로 정리한다."""
    if value is None or value is pd.NA:
        return ""
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass
    return str(value).strip()


def _clean_keyword(value: object) -> str:
    """저장 전 키워드 토큰 하나를 공백 기준으로 정리한다."""
    text = _text_or_empty(value).lstrip("#").strip()
    return re.sub(r"\s+", " ", text)


def normalize_it_keywords(
    value: object,
    max_keywords: int = AnalyzeItKeywordsConfig.MAX_KEYWORDS,
) -> str:
    """IC02 회사/분류 값을 `#회사명#분류` 형식으로 정규화한다."""
    if isinstance(value, str):
        parts = value.split("#") if "#" in value else [value]
    elif isinstance(value, list):
        parts = value
    else:
        parts = []

    normalized: list[str] = []
    for part in parts:
        keyword = _clean_keyword(part)
        if not keyword:
            continue
        normalized.append(keyword)
        if len(normalized) >= max_keywords:
            break
    return "".join(f"#{keyword}" for keyword in normalized)


def get_it_keyword_worker_count(workers: int | None = None) -> int:
    """기존 pipeline 인자 호환을 위해 worker 값의 유효성만 검증한다."""
    resolved = workers if workers is not None else AnalyzeItKeywordsConfig.DEFAULT_WORKERS
    if resolved < AnalyzeItKeywordsConfig.MIN_POSITIVE_CONFIG_VALUE:
        raise ValueError("it_keywords_workers must be greater than 0")
    return resolved


def analyze_it_keyword_row(
    row: dict | pd.Series,
    *,
    tokenizer: BertTokenizer,
) -> ItKeywordAnalysisResult:
    """IC02 row 하나에서 회사/분류 키워드와 제목 감성을 만든다."""
    title = _text_or_empty(row.get(AnalysisColumn.TITLE.value))
    if not title:
        raise ValueError("IC02 title is required for title sentiment analysis")

    content = _text_or_empty(row.get(AnalysisColumn.CONTENT.value))
    companies = match_it_companies(title=title, content=content)
    keywords = normalize_it_keywords(build_company_keyword_values(companies)) or None
    sentiment = tokenizer.predict_sentiment(title)
    sentimental = sentiment[SentimentResultKey.SENTIMENTAL.value]
    score = float(sentiment[SentimentResultKey.SCORE.value])
    return ItKeywordAnalysisResult(
        keywords=keywords,
        sentimental=str(sentimental),
        score=score,
    )


def _is_blank_series(series: pd.Series) -> pd.Series:
    """문자열 column의 결측 또는 공백 여부를 반환한다."""
    empty_map = {value: pd.NA for value in AnalyzeItKeywordsConfig.CONTENT_EMPTY_PLACEHOLDERS}
    normalized = series.replace(empty_map)
    return normalized.isna() | normalized.astype(str).str.strip().eq("")


def _validate_required_columns(df: pd.DataFrame) -> None:
    """IC02 회사/감성 처리에 필요한 analysis column을 검증한다."""
    required = (
        AnalysisColumn.CRAWLING_ID.value,
        AnalysisColumn.TITLE.value,
        AnalysisColumn.CONTENT.value,
        AnalysisColumn.KEYWORDS.value,
        AnalysisColumn.INFORMATION_CD.value,
        AnalysisColumn.SENTIMENTAL.value,
        AnalysisColumn.SCORE.value,
    )
    missing = [column for column in required if column not in df.columns]
    if missing:
        raise ValueError(PostAnalysisErrors.ItKeywords.missing_columns(missing))


def _filter_it_keyword_targets(df: pd.DataFrame, *, overwrite: bool) -> pd.DataFrame:
    """IC02 전용 회사/감성 처리 대상 row만 남긴다."""
    info_col = AnalysisColumn.INFORMATION_CD.value
    title_col = AnalysisColumn.TITLE.value
    content_col = AnalysisColumn.CONTENT.value
    sentimental_col = AnalysisColumn.SENTIMENTAL.value
    score_col = AnalysisColumn.SCORE.value

    df = df[df[info_col] == CodeTable.INFORMATION_IT_INFO.value].copy()
    has_title = ~_is_blank_series(df[title_col])
    has_content = ~_is_blank_series(df[content_col])
    df = df[has_title | has_content].copy()
    if overwrite:
        return df

    missing_sentimental = _is_blank_series(df[sentimental_col])
    missing_score = _is_blank_series(df[score_col])
    return df[missing_sentimental | missing_score].copy()


def _build_update_row(crawling_id: object, result: ItKeywordAnalysisResult) -> dict[str, object]:
    """MERGE에 보낼 IC02 update row를 만든다."""
    return {
        AnalysisColumn.CRAWLING_ID.value: crawling_id,
        AnalysisColumn.KEYWORDS.value: result.keywords,
        AnalysisColumn.SENTIMENTAL.value: result.sentimental,
        AnalysisColumn.SCORE.value: result.score,
    }


def analyze_it_keywords(
    max_rows: int | None = None,
    overwrite: bool = False,
    workers: int | None = None,
) -> None:
    """IC02 IT news row에 회사/분류 키워드와 제목 감성을 저장한다."""
    get_it_keyword_worker_count(workers)
    df = get_it_keyword_target_data(overwrite=overwrite, max_rows=max_rows)
    _validate_required_columns(df)

    df = _filter_it_keyword_targets(df, overwrite=overwrite)
    if df.empty:
        logger.debug(PostAnalysisErrors.ItKeywords.no_pending_rows())
        return

    tokenizer = BertTokenizer()
    updates: list[dict[str, object]] = []
    for index, row in df.iterrows():
        crawling_id = row[AnalysisColumn.CRAWLING_ID.value]
        try:
            result = analyze_it_keyword_row(row, tokenizer=tokenizer)
        except Exception:
            logger.exception(PostAnalysisErrors.ItKeywords.row_processing_failed(), crawling_id, index)
            continue
        updates.append(_build_update_row(crawling_id, result))

    if not updates:
        logger.debug(PostAnalysisErrors.ItKeywords.no_successful_rows())
        return

    merge_analysis_data(pd.DataFrame(updates))
    logger.debug("IC02 company/sentiment analysis completed rows=%s", len(updates))


if __name__ == "__main__":
    _configure_cli_logging()
    analyze_it_keywords()
