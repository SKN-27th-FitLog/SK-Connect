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
