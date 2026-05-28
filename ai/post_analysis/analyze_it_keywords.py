"""IC02 IT 뉴스 전용 키워드 분석으로 `analysis.keywords`를 채운다."""

from __future__ import annotations

import json
import logging
import os
import re
import urllib.error
import urllib.request
from typing import Any

import pandas as pd
from pydantic import BaseModel, Field

import common.env  # noqa: F401 - DB/Ollama 환경변수 로드
from common.constant import AnalysisColumn, AnalyzeItKeywordsConfig, CodeTable, CrawlingColumn
from common.errors import PostAnalysisErrors
from postgresql.run_query import get_analysis_data, get_crawling_data, merge_analysis_data

logger = logging.getLogger(__name__)


class ItKeywordResult(BaseModel):
    """IC02 IT 키워드 LLM 응답 구조."""

    summary: str = ""
    flow: str = ""
    interest_label: str = ""
    keywords: list[str] = Field(default_factory=list)


def get_ollama_model_name() -> str:
    """IC02 키워드 분석에 사용할 Ollama 모델명을 반환한다."""
    value = os.environ.get(AnalyzeItKeywordsConfig.MODEL_ENV_KEY)
    return value.strip() if value and value.strip() else AnalyzeItKeywordsConfig.DEFAULT_MODEL


def get_ollama_base_url() -> str:
    """Ollama HTTP API base URL을 반환한다."""
    value = os.environ.get(AnalyzeItKeywordsConfig.OLLAMA_BASE_URL_ENV_KEY)
    base_url = value.strip() if value and value.strip() else AnalyzeItKeywordsConfig.DEFAULT_OLLAMA_BASE_URL
    return base_url.rstrip("/")


def _number_or_zero(value: object) -> float:
    """관심도 계산용 숫자 변환. 결측·변환 실패는 0."""
    if value is None or value is pd.NA:
        return 0.0
    try:
        if pd.isna(value):
            return 0.0
    except (TypeError, ValueError):
        pass
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


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


def compute_interest_signal(row: dict | pd.Series) -> dict[str, object]:
    """view/comment/point 기반 관심도 신호를 계산한다."""
    view_count = max(_number_or_zero(row.get(CrawlingColumn.VIEW_COUNT.value)), 0.0)
    comment_count = max(_number_or_zero(row.get(CrawlingColumn.COMMENT_COUNT.value)), 0.0)
    point = max(_number_or_zero(row.get(CrawlingColumn.POINT.value)), 0.0)
    score = int(
        view_count
        + comment_count * AnalyzeItKeywordsConfig.INTEREST_COMMENT_WEIGHT
        + point * AnalyzeItKeywordsConfig.INTEREST_POINT_WEIGHT
    )
    if score >= AnalyzeItKeywordsConfig.INTEREST_HIGH_THRESHOLD:
        level = "high"
    elif score >= AnalyzeItKeywordsConfig.INTEREST_MEDIUM_THRESHOLD:
        level = "medium"
    else:
        level = "low"
    return {
        "score": score,
        "level": level,
        "description": (
            f"view_count={int(view_count)}, comment_count={int(comment_count)}, "
            f"point={point:g}, interest_score={score}, interest_level={level}"
        ),
    }


def _clean_keyword(value: object) -> str:
    """키워드 하나를 downstream 호환 문자열로 정리한다."""
    text = _text_or_empty(value).lstrip("#").strip()
    return re.sub(r"\s+", " ", text)


def normalize_it_keywords(value: object, max_keywords: int = AnalyzeItKeywordsConfig.MAX_KEYWORDS) -> str:
    """LLM 키워드 결과를 `#키워드1#키워드2` 형식으로 정규화한다."""
    if isinstance(value, str):
        parts = value.split("#") if "#" in value else [value]
    elif isinstance(value, list):
        parts = value
    else:
        parts = []

    seen: set[str] = set()
    normalized: list[str] = []
    for part in parts:
        keyword = _clean_keyword(part)
        if not keyword or keyword in seen:
            continue
        seen.add(keyword)
        normalized.append(keyword)
        if len(normalized) >= max_keywords:
            break
    return "".join(f"#{keyword}" for keyword in normalized)


def build_it_keyword_prompt(row: dict | pd.Series) -> str:
    """Gemma용 단일 user prompt를 만든다."""
    title = _text_or_empty(row.get(AnalysisColumn.TITLE.value))
    content = _text_or_empty(row.get(AnalysisColumn.CONTENT.value))
    interest = compute_interest_signal(row)
    return "\n".join(
        [
            "당신은 IT 뉴스 게시글 기획을 위한 키워드 분석기입니다.",
            "입력 글을 읽고 요약, 글의 흐름, 관심도 라벨, 게시글 생성용 키워드를 JSON으로만 반환하세요.",
            "키워드는 기술 주제와 게시글 관점을 함께 포함해야 합니다.",
            "반환 JSON 스키마:",
            '{"summary":"릴리스 핵심 요약","flow":"발표 -> 변화 -> 영향","interest_label":"high","keywords":["PyTorch","추론 성능","배포 영향"]}',
            "제약:",
            "- keywords는 3개 이상 7개 이하입니다.",
            "- keywords에는 기술명/제품명/프레임워크와 영향/리스크/활용 포인트를 함께 넣습니다.",
            "- 원문에 없는 세부 사실을 만들지 않습니다.",
            "- JSON 외 텍스트를 출력하지 않습니다.",
            "",
            f"[title]\n{title}",
            f"[content]\n{content}",
            f"[interest]\n{interest['description']}",
        ]
    )


def _ollama_chat_json(prompt: str) -> dict[str, Any]:
    """Ollama chat API를 호출하고 JSON content를 dict로 반환한다."""
    payload = {
        "model": get_ollama_model_name(),
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "format": "json",
    }
    request = urllib.request.Request(
        f"{get_ollama_base_url()}/api/chat",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(
            request,
            timeout=AnalyzeItKeywordsConfig.REQUEST_TIMEOUT_SECONDS,
        ) as response:
            response_data = json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Ollama IC02 keyword request failed: {exc}") from exc

    content = response_data.get("message", {}).get("content", "")
    if not content:
        raise ValueError("Ollama response did not include message.content")
    return json.loads(content)


def extract_it_keywords(row: dict | pd.Series) -> ItKeywordResult:
    """IC02 row 하나를 Ollama로 분석해 요약, 흐름, 키워드를 추출한다."""
    prompt = build_it_keyword_prompt(row)
    return ItKeywordResult(**_ollama_chat_json(prompt))


def _is_blank_series(series: pd.Series) -> pd.Series:
    """문자열 column의 결측 또는 공백 여부를 반환한다."""
    empty_map = {value: pd.NA for value in AnalyzeItKeywordsConfig.CONTENT_EMPTY_PLACEHOLDERS}
    normalized = series.replace(empty_map)
    return normalized.isna() | normalized.astype(str).str.strip().eq("")


def _validate_required_columns(df: pd.DataFrame) -> None:
    """IC02 keyword 분석에 필요한 analysis column을 검증한다."""
    required = (
        AnalysisColumn.CRAWLING_ID.value,
        AnalysisColumn.TITLE.value,
        AnalysisColumn.CONTENT.value,
        AnalysisColumn.KEYWORDS.value,
        AnalysisColumn.INFORMATION_CD.value,
    )
    missing = [column for column in required if column not in df.columns]
    if missing:
        raise ValueError(PostAnalysisErrors.ItKeywords.missing_columns(missing))


def _attach_crawling_metrics(df: pd.DataFrame, df_crawling: pd.DataFrame) -> pd.DataFrame:
    """analysis row에 crawling 관심도 metric을 붙인다."""
    id_col = AnalysisColumn.CRAWLING_ID.value
    metric_cols = (
        CrawlingColumn.VIEW_COUNT.value,
        CrawlingColumn.COMMENT_COUNT.value,
        CrawlingColumn.POINT.value,
    )
    out = df.copy()
    if id_col not in df_crawling.columns:
        for column in metric_cols:
            out[column] = 0
        return out

    available = [id_col, *[column for column in metric_cols if column in df_crawling.columns]]
    metrics = df_crawling[available].drop_duplicates(subset=[id_col], keep="last")
    out = out.merge(metrics, on=id_col, how="left")
    for column in metric_cols:
        if column not in out.columns:
            out[column] = 0
    return out


def _filter_it_keyword_targets(df: pd.DataFrame, *, overwrite: bool) -> pd.DataFrame:
    """IC02 전용 keyword 처리 대상 row만 남긴다."""
    info_col = AnalysisColumn.INFORMATION_CD.value
    title_col = AnalysisColumn.TITLE.value
    content_col = AnalysisColumn.CONTENT.value
    kw_col = AnalysisColumn.KEYWORDS.value

    df = df[df[info_col] == CodeTable.INFORMATION_IT_INFO.value].copy()
    has_title = ~_is_blank_series(df[title_col])
    has_content = ~_is_blank_series(df[content_col])
    df = df[has_title | has_content].copy()
    if overwrite:
        return df
    return df[_is_blank_series(df[kw_col])].copy()


def analyze_it_keywords(max_rows: int | None = None, overwrite: bool = False) -> None:
    """IC02 IT news row의 `analysis.keywords`만 채운다."""
    df = get_analysis_data()
    _validate_required_columns(df)

    df = _filter_it_keyword_targets(df, overwrite=overwrite)
    if df.empty:
        logger.info(PostAnalysisErrors.ItKeywords.no_pending_rows())
        return

    if max_rows is not None and max_rows > 0:
        df = df.head(max_rows).copy()
        logger.info("IC02 IT keyword limit applied: %s rows (max_rows=%s)", len(df), max_rows)

    df = _attach_crawling_metrics(df, get_crawling_data())
    kw_col = AnalysisColumn.KEYWORDS.value
    id_col = AnalysisColumn.CRAWLING_ID.value
    df[kw_col] = df[kw_col].astype(AnalyzeItKeywordsConfig.DTYPE_OBJECT)

    success_indexes: list[int] = []
    for index, row in df.iterrows():
        crawling_id = row.get(id_col)
        try:
            result = extract_it_keywords(row)
            keywords = normalize_it_keywords(result.keywords)
            if not keywords:
                logger.info("IC02 IT keyword empty result skipped (crawling_id=%s)", crawling_id)
                continue
            df.at[index, kw_col] = keywords
            success_indexes.append(index)
            logger.info(
                "IC02 IT keywords: crawling_id=%s interest=%s keywords=%s",
                crawling_id,
                result.interest_label,
                keywords,
            )
        except Exception:
            logger.exception(
                PostAnalysisErrors.ItKeywords.row_processing_failed(),
                crawling_id,
                index,
            )
            continue

    if not success_indexes:
        logger.info(PostAnalysisErrors.ItKeywords.no_successful_rows())
        return

    merge_columns = [id_col, kw_col]
    merge_analysis_data(df.loc[success_indexes, merge_columns].copy())
    logger.info("IC02 IT keyword extraction completed (%s rows)", len(success_indexes))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s [%(name)s] %(message)s")
    analyze_it_keywords()
