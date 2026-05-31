# IC02 IT Keywords Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an IC02-only IT news keyword analysis stage in `ai/post_analysis` that uses Ollama `gemma4:26b`, summary/flow/interest context, and writes only `analysis.keywords`.

**Architecture:** Keep existing IC01 meal analysis untouched. Add a new `analyze_it_keywords.py` module with pure helpers, a minimal stdlib Ollama JSON client, row filtering, and merge orchestration. Wire it into `pipeline.py` as the final step with separate CLI flags.

**Tech Stack:** Python, pandas, pydantic, urllib stdlib Ollama HTTP API, pytest, PostgreSQL read helpers already present in `post_analysis`.

---

## Scope Guard

Only touch these implementation files:

- Create: `ai/post_analysis/analyze_it_keywords.py`
- Modify: `ai/post_analysis/common/constant.py`
- Modify: `ai/post_analysis/common/errors.py`
- Modify: `ai/post_analysis/pipeline.py`
- Modify: `ai/post_analysis/tests/conftest.py`
- Create: `ai/post_analysis/tests/unit/test_l0_it_keywords.py`
- Create: `ai/post_analysis/tests/unit/test_l3_analyze_it_keywords_indirect.py`
- Modify: `ai/post_analysis/tests/unit/test_l3_run_pipeline_indirect.py`

Do not modify:

- `ai/post_analysis/get_reviews.py`
- `ai/post_analysis/analyze_sentimental.py`
- `ai/post_analysis/analyze_keywords.py`
- `ai/post_analysis/postgresql/config.py`
- `ai/post_analysis/postgresql/run_query.py`
- `etl/meal`
- `etl/it_news`
- `ai/postmake_pipeline`
- DB schema files

## File Responsibilities

- `analyze_it_keywords.py`: IC02-only keyword extraction, interest signal calculation, Ollama call, response validation, DataFrame merge input construction.
- `common/constant.py`: IC02 keyword config constants only.
- `common/errors.py`: IC02 keyword error/log messages only.
- `pipeline.py`: add final IC02 keyword step and CLI flags without changing existing IC01 step behavior.
- `tests/conftest.py`: extend merge guard to the new module.
- New tests: pure helper tests and indirect orchestration tests.

---

### Task 1: Add IC02 Config And Error Contracts

**Files:**
- Modify: `ai/post_analysis/common/constant.py`
- Modify: `ai/post_analysis/common/errors.py`
- Test: `ai/post_analysis/tests/unit/test_l0_it_keywords.py`

- [ ] **Step 1: Write failing tests for config and error messages**

Create `ai/post_analysis/tests/unit/test_l0_it_keywords.py` with this initial content:

```python
"""PA-L0-ITKW: IC02 IT keyword pure helpers and config."""

import pytest

from common.constant import AnalyzeItKeywordsConfig
from common.errors import PostAnalysisErrors


def test_pa_l0_itkw_001_config_defaults() -> None:
    """PA-L0-ITKW-001 [불변]: IC02 키워드 기본 모델과 관심도 기준."""
    assert AnalyzeItKeywordsConfig.DEFAULT_MODEL == "gemma4:26b"
    assert AnalyzeItKeywordsConfig.MODEL_ENV_KEY == "POST_ANALYSIS_IT_KEYWORDS_MODEL"
    assert AnalyzeItKeywordsConfig.OLLAMA_BASE_URL_ENV_KEY == "OLLAMA_BASE_URL"
    assert AnalyzeItKeywordsConfig.MIN_KEYWORDS == 12
    assert AnalyzeItKeywordsConfig.MAX_KEYWORDS == 15
    assert AnalyzeItKeywordsConfig.INTEREST_HIGH_THRESHOLD == 1000
    assert AnalyzeItKeywordsConfig.INTEREST_MEDIUM_THRESHOLD == 100


def test_pa_l0_itkw_002_error_messages() -> None:
    """PA-L0-ITKW-002 [정상]: IC02 키워드 오류 메시지가 독립 namespace에 있다."""
    assert "IT 키워드" in PostAnalysisErrors.ItKeywords.missing_columns(["title"])
    assert "처리할" in PostAnalysisErrors.ItKeywords.no_pending_rows()
    assert "crawling_id" in PostAnalysisErrors.ItKeywords.row_processing_failed()
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```powershell
C:\Python314\python.exe -m pytest ai\post_analysis\tests\unit\test_l0_it_keywords.py -v
```

Expected: FAIL because `AnalyzeItKeywordsConfig` and `PostAnalysisErrors.ItKeywords` do not exist.

- [ ] **Step 3: Add `AnalyzeItKeywordsConfig`**

Append this class to `ai/post_analysis/common/constant.py` after `AnalyzeKeywordsConfig`:

```python
class AnalyzeItKeywordsConfig:
    """IC02 IT 뉴스 키워드 분석 배치 설정."""

    MODEL_ENV_KEY = "POST_ANALYSIS_IT_KEYWORDS_MODEL"
    OLLAMA_BASE_URL_ENV_KEY = "OLLAMA_BASE_URL"
    DEFAULT_MODEL = "gemma4:26b"
    DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434"
    REQUEST_TIMEOUT_SECONDS = 120
    MIN_KEYWORDS = 12
    MAX_KEYWORDS = 15
    DTYPE_OBJECT = "object"
    CONTENT_EMPTY_PLACEHOLDERS = ("", "-", "N/A")
    INTEREST_COMMENT_WEIGHT = 10
    INTEREST_POINT_WEIGHT = 20
    INTEREST_HIGH_THRESHOLD = 1000
    INTEREST_MEDIUM_THRESHOLD = 100
```

- [ ] **Step 4: Add `ItKeywords` errors**

Add this nested class in `PostAnalysisErrors`, next to `AnalyzeKeywords`:

```python
    class ItKeywords:
        """``analyze_it_keywords`` 단계 오류·로그 메시지 (Level 0, 유형 B)."""

        @staticmethod
        def missing_columns(missing: Iterable[str]) -> str:
            """필수 analysis 컬럼 누락 ``ValueError`` 메시지."""
            return _missing_columns_message("analysis", "IT 키워드 추출", missing)

        @staticmethod
        def no_pending_rows() -> str:
            """IC02 키워드 처리 대상 0건일 때 ``logger.info`` 메시지."""
            return "IC02 IT 키워드 처리할 행이 없습니다."

        @staticmethod
        def no_successful_rows() -> str:
            """행별 처리 후 저장 가능한 성공 행 0건일 때 ``logger.info`` 메시지."""
            return "IC02 IT 키워드 성공 행이 없어 MERGE를 생략합니다."

        @staticmethod
        def row_processing_failed() -> str:
            """행별 IC02 키워드 추출 실패 ``logger.exception`` 포맷 문자열."""
            return "IC02 IT 키워드 처리 실패 (crawling_id=%s, index=%s)"
```

- [ ] **Step 5: Run tests and verify they pass**

Run:

```powershell
C:\Python314\python.exe -m pytest ai\post_analysis\tests\unit\test_l0_it_keywords.py -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

```powershell
git add ai\post_analysis\common\constant.py ai\post_analysis\common\errors.py ai\post_analysis\tests\unit\test_l0_it_keywords.py
git commit -m "feat: add ic02 keyword config contracts"
```

---

### Task 2: Add Pure IC02 Keyword Helpers

**Files:**
- Create: `ai/post_analysis/analyze_it_keywords.py`
- Modify: `ai/post_analysis/tests/unit/test_l0_it_keywords.py`

- [ ] **Step 1: Add failing pure helper tests**

Append these tests to `ai/post_analysis/tests/unit/test_l0_it_keywords.py`:

```python
import pandas as pd

from analyze_it_keywords import (
    ItKeywordResult,
    build_it_keyword_prompt,
    compute_interest_signal,
    get_ollama_base_url,
    get_ollama_model_name,
    normalize_it_keywords,
)


def test_pa_l0_itkw_003_normalize_keywords_list() -> None:
    """PA-L0-ITKW-003 [정상]: list 키워드를 # 구분 문자열로 정규화한다."""
    assert normalize_it_keywords([" PyTorch ", "PyTorch", "", "#GPU 비용"]) == "#PyTorch#GPU 비용"


def test_pa_l0_itkw_004_normalize_keywords_string() -> None:
    """PA-L0-ITKW-004 [정상]: 기존 # 문자열도 중복 제거한다."""
    assert normalize_it_keywords("#PyTorch# GPU 비용 #PyTorch") == "#PyTorch#GPU 비용"


def test_pa_l0_itkw_005_interest_signal_high_medium_low() -> None:
    """PA-L0-ITKW-005 [정상]: view/comment/point 기반 관심도 등급."""
    high = compute_interest_signal({"view_count": 800, "comment_count": 10, "point": 5})
    medium = compute_interest_signal({"view_count": 80, "comment_count": 2, "point": 0})
    low = compute_interest_signal({"view_count": None, "comment_count": pd.NA, "point": -3})
    assert high["level"] == "high"
    assert high["score"] == 1000
    assert medium["level"] == "medium"
    assert low["level"] == "low"
    assert low["score"] == 0


def test_pa_l0_itkw_006_prompt_contains_summary_flow_interest() -> None:
    """PA-L0-ITKW-006 [정상]: 프롬프트에 요약·흐름·관심도 요구가 포함된다."""
    prompt = build_it_keyword_prompt(
        {
            "title": "PyTorch 2.5 릴리스",
            "content": "추론 성능과 배포 편의성이 개선되었습니다.",
            "view_count": 1200,
            "comment_count": 8,
            "point": 3,
        }
    )
    assert "summary" in prompt
    assert "flow" in prompt
    assert "interest_label" in prompt
    assert "keywords" in prompt
    assert "PyTorch 2.5 릴리스" in prompt


def test_pa_l0_itkw_007_ollama_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    """PA-L0-ITKW-007 [정상]: Ollama 모델과 base URL은 환경변수로 바꿀 수 있다."""
    monkeypatch.setenv("POST_ANALYSIS_IT_KEYWORDS_MODEL", "gemma4:e4b")
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434/")
    assert get_ollama_model_name() == "gemma4:e4b"
    assert get_ollama_base_url() == "http://127.0.0.1:11434"


def test_pa_l0_itkw_008_response_model() -> None:
    """PA-L0-ITKW-008 [정상]: LLM 응답 모델은 summary/flow/interest_label/keywords를 가진다."""
    result = ItKeywordResult(
        summary="릴리스 요약",
        flow="발표 -> 영향",
        interest_label="high",
        keywords=["PyTorch", "추론 성능"],
    )
    assert result.keywords == ["PyTorch", "추론 성능"]
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```powershell
C:\Python314\python.exe -m pytest ai\post_analysis\tests\unit\test_l0_it_keywords.py -v
```

Expected: FAIL because `analyze_it_keywords.py` does not exist.

- [ ] **Step 3: Create `analyze_it_keywords.py` with pure helpers**

Create `ai/post_analysis/analyze_it_keywords.py` with this initial implementation:

```python
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

import common.env  # noqa: F401 — DB/Ollama 환경변수 로드
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
    text = str(value or "").strip().lstrip("#").strip()
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
    title = str(row.get(AnalysisColumn.TITLE.value) or "").strip()
    content = str(row.get(AnalysisColumn.CONTENT.value) or "").strip()
    interest = compute_interest_signal(row)
    return "\n".join(
        [
            "당신은 IT 뉴스 게시글 기획을 위한 키워드 분석기입니다.",
            "입력 글을 읽고 요약, 글의 흐름, 관심도 라벨, 게시글 생성용 키워드를 JSON으로만 반환하세요.",
            "키워드는 기술 주제와 게시글 관점을 함께 포함해야 합니다.",
            "반환 JSON 스키마:",
            '{"summary":"릴리스 핵심 요약","flow":"발표 -> 변화 -> 영향","interest_label":"high","keywords":["PyTorch 2.8","추론 성능 개선","GPU 비용","배포 효율","API 변경","모델 최적화","서버 지연 시간","운영 비용","개발자 영향","프로덕션 배포","성능 검토","AI 인프라"]}',
            "제약:",
            "- keywords는 12개 이상 15개 이하입니다.",
            "- keywords에는 기술명, 제품명, 프레임워크, 변경점, 영향, 리스크, 활용 포인트, 독자 관점을 균형 있게 넣습니다.",
            "- 원문에 없는 세부 사실을 만들지 않습니다.",
            "- JSON 외 텍스트를 출력하지 않습니다.",
            "",
            f"[title]\n{title}",
            f"[content]\n{content}",
            f"[interest]\n{interest['description']}",
        ]
    )
```

- [ ] **Step 4: Run pure helper tests**

Run:

```powershell
C:\Python314\python.exe -m pytest ai\post_analysis\tests\unit\test_l0_it_keywords.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add ai\post_analysis\analyze_it_keywords.py ai\post_analysis\tests\unit\test_l0_it_keywords.py
git commit -m "feat: add ic02 keyword helper functions"
```

---

### Task 3: Add Ollama Extraction And IC02 Orchestration

**Files:**
- Modify: `ai/post_analysis/analyze_it_keywords.py`
- Modify: `ai/post_analysis/tests/conftest.py`
- Create: `ai/post_analysis/tests/unit/test_l3_analyze_it_keywords_indirect.py`

- [ ] **Step 1: Add merge guard target**

Modify `ai/post_analysis/tests/conftest.py` and add the new target to `targets`:

```python
        "analyze_it_keywords.merge_analysis_data",
```

The full `targets` tuple should include:

```python
    targets = (
        "postgresql.run_query.merge_analysis_data",
        "get_reviews.merge_analysis_data",
        "analyze_sentimental.merge_analysis_data",
        "analyze_keywords.merge_analysis_data",
        "analyze_keywords_by_llm.merge_analysis_data",
        "analyze_it_keywords.merge_analysis_data",
    )
```

- [ ] **Step 2: Write failing orchestration tests**

Create `ai/post_analysis/tests/unit/test_l3_analyze_it_keywords_indirect.py`:

```python
"""PA-L3-ITKW: analyze_it_keywords 간접 검증 (Ollama·merge patch)."""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from analyze_it_keywords import ItKeywordResult, analyze_it_keywords
from common.constant import AnalysisColumn, CodeTable, CrawlingColumn


def _analysis_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            AnalysisColumn.CRAWLING_ID.value: [101, 102, 103],
            AnalysisColumn.TITLE.value: ["IT A", "Meal B", "IT C"],
            AnalysisColumn.CONTENT.value: ["PyTorch update", "맛집 리뷰", "GPU news"],
            AnalysisColumn.KEYWORDS.value: [pd.NA, pd.NA, "#existing"],
            AnalysisColumn.INFORMATION_CD.value: [
                CodeTable.INFORMATION_IT_INFO.value,
                CodeTable.INFORMATION_RESTAURANT.value,
                CodeTable.INFORMATION_IT_INFO.value,
            ],
        }
    )


def _crawling_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            CrawlingColumn.CRAWLING_ID.value: [101, 103],
            CrawlingColumn.VIEW_COUNT.value: [1200, 10],
            CrawlingColumn.COMMENT_COUNT.value: [8, 0],
            CrawlingColumn.POINT.value: [3, 0],
        }
    )


@patch("analyze_it_keywords.merge_analysis_data")
@patch("analyze_it_keywords.extract_it_keywords")
@patch("analyze_it_keywords.get_crawling_data")
@patch("analyze_it_keywords.get_analysis_data")
def test_pa_l3_itkw_001_processes_ic02_missing_keywords_only(
    mock_get_analysis: MagicMock,
    mock_get_crawling: MagicMock,
    mock_extract: MagicMock,
    mock_merge: MagicMock,
) -> None:
    """PA-L3-ITKW-001 [정상]: 기본 실행은 IC02 중 keywords 결측만 처리한다."""
    mock_get_analysis.return_value = _analysis_df()
    mock_get_crawling.return_value = _crawling_df()
    mock_extract.return_value = ItKeywordResult(
        summary="요약",
        flow="발표 -> 영향",
        interest_label="high",
        keywords=["PyTorch", "추론 성능", "높은 커뮤니티 관심"],
    )

    analyze_it_keywords()

    mock_extract.assert_called_once()
    mock_merge.assert_called_once()
    df = mock_merge.call_args[0][0]
    assert len(df) == 1
    assert df[AnalysisColumn.CRAWLING_ID.value].iloc[0] == 101
    assert df[AnalysisColumn.KEYWORDS.value].iloc[0] == "#PyTorch#추론 성능#높은 커뮤니티 관심"


@patch("analyze_it_keywords.merge_analysis_data")
@patch("analyze_it_keywords.extract_it_keywords")
@patch("analyze_it_keywords.get_crawling_data")
@patch("analyze_it_keywords.get_analysis_data")
def test_pa_l3_itkw_002_overwrite_reprocesses_existing_ic02(
    mock_get_analysis: MagicMock,
    mock_get_crawling: MagicMock,
    mock_extract: MagicMock,
    mock_merge: MagicMock,
) -> None:
    """PA-L3-ITKW-002 [정상]: overwrite=True면 기존 IC02 keywords도 재처리한다."""
    mock_get_analysis.return_value = _analysis_df()
    mock_get_crawling.return_value = _crawling_df()
    mock_extract.return_value = ItKeywordResult(
        summary="요약",
        flow="발표 -> 영향",
        interest_label="medium",
        keywords=["GPU", "개발자 영향"],
    )

    analyze_it_keywords(overwrite=True)

    assert mock_extract.call_count == 2
    mock_merge.assert_called_once()
    assert list(mock_merge.call_args[0][0][AnalysisColumn.CRAWLING_ID.value]) == [101, 103]


@patch("analyze_it_keywords.merge_analysis_data")
@patch("analyze_it_keywords.extract_it_keywords")
@patch("analyze_it_keywords.get_crawling_data")
@patch("analyze_it_keywords.get_analysis_data")
def test_pa_l3_itkw_003_max_rows_limits_after_filter(
    mock_get_analysis: MagicMock,
    mock_get_crawling: MagicMock,
    mock_extract: MagicMock,
    mock_merge: MagicMock,
) -> None:
    """PA-L3-ITKW-003 [경계]: max_rows는 IC02 필터 이후 적용된다."""
    mock_get_analysis.return_value = pd.DataFrame(
        {
            AnalysisColumn.CRAWLING_ID.value: [1, 2, 3],
            AnalysisColumn.TITLE.value: ["A", "B", "C"],
            AnalysisColumn.CONTENT.value: ["a", "b", "c"],
            AnalysisColumn.KEYWORDS.value: [pd.NA, pd.NA, pd.NA],
            AnalysisColumn.INFORMATION_CD.value: [CodeTable.INFORMATION_IT_INFO.value] * 3,
        }
    )
    mock_get_crawling.return_value = pd.DataFrame()
    mock_extract.return_value = ItKeywordResult(keywords=["키워드"])

    analyze_it_keywords(max_rows=2)

    assert mock_extract.call_count == 2
    assert len(mock_merge.call_args[0][0]) == 2


@patch("analyze_it_keywords.merge_analysis_data")
@patch("analyze_it_keywords.extract_it_keywords")
@patch("analyze_it_keywords.get_crawling_data")
@patch("analyze_it_keywords.get_analysis_data")
def test_pa_l3_itkw_004_row_failure_merges_successes_only(
    mock_get_analysis: MagicMock,
    mock_get_crawling: MagicMock,
    mock_extract: MagicMock,
    mock_merge: MagicMock,
) -> None:
    """PA-L3-ITKW-004 [부분 실패]: row 실패는 계속 진행하고 성공분만 MERGE한다."""
    mock_get_analysis.return_value = pd.DataFrame(
        {
            AnalysisColumn.CRAWLING_ID.value: [1, 2],
            AnalysisColumn.TITLE.value: ["A", "B"],
            AnalysisColumn.CONTENT.value: ["a", "b"],
            AnalysisColumn.KEYWORDS.value: [pd.NA, pd.NA],
            AnalysisColumn.INFORMATION_CD.value: [CodeTable.INFORMATION_IT_INFO.value] * 2,
        }
    )
    mock_get_crawling.return_value = pd.DataFrame()
    mock_extract.side_effect = [RuntimeError("ollama down"), ItKeywordResult(keywords=["성공"])]

    analyze_it_keywords()

    mock_merge.assert_called_once()
    df = mock_merge.call_args[0][0]
    assert list(df[AnalysisColumn.CRAWLING_ID.value]) == [2]
    assert df[AnalysisColumn.KEYWORDS.value].iloc[0] == "#성공"


@patch("analyze_it_keywords.merge_analysis_data")
@patch("analyze_it_keywords.extract_it_keywords")
@patch("analyze_it_keywords.get_crawling_data")
@patch("analyze_it_keywords.get_analysis_data")
def test_pa_l3_itkw_005_no_success_skips_merge(
    mock_get_analysis: MagicMock,
    mock_get_crawling: MagicMock,
    mock_extract: MagicMock,
    mock_merge: MagicMock,
) -> None:
    """PA-L3-ITKW-005 [경계]: 추출 결과가 모두 비면 MERGE하지 않는다."""
    mock_get_analysis.return_value = pd.DataFrame(
        {
            AnalysisColumn.CRAWLING_ID.value: [1],
            AnalysisColumn.TITLE.value: ["A"],
            AnalysisColumn.CONTENT.value: ["a"],
            AnalysisColumn.KEYWORDS.value: [pd.NA],
            AnalysisColumn.INFORMATION_CD.value: [CodeTable.INFORMATION_IT_INFO.value],
        }
    )
    mock_get_crawling.return_value = pd.DataFrame()
    mock_extract.return_value = ItKeywordResult(keywords=[])

    analyze_it_keywords()

    mock_merge.assert_not_called()


@patch("analyze_it_keywords.merge_analysis_data")
@patch("analyze_it_keywords.extract_it_keywords")
@patch("analyze_it_keywords.get_analysis_data")
def test_pa_l3_itkw_006_missing_columns(
    mock_get_analysis: MagicMock,
    mock_extract: MagicMock,
    mock_merge: MagicMock,
) -> None:
    """PA-L3-ITKW-006 [실패]: 필수 컬럼 누락 시 ValueError."""
    mock_get_analysis.return_value = pd.DataFrame({AnalysisColumn.TITLE.value: ["A"]})

    with pytest.raises(ValueError, match="IT 키워드"):
        analyze_it_keywords()

    mock_extract.assert_not_called()
    mock_merge.assert_not_called()
```

- [ ] **Step 3: Run tests and verify they fail**

Run:

```powershell
C:\Python314\python.exe -m pytest ai\post_analysis\tests\unit\test_l3_analyze_it_keywords_indirect.py -v
```

Expected: FAIL because orchestration functions are not implemented.

- [ ] **Step 4: Add orchestration helpers and Ollama extraction**

Append this code to `ai/post_analysis/analyze_it_keywords.py` after `build_it_keyword_prompt`:

```python
def _ollama_chat_json(prompt: str) -> dict:
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
    """IC02 row 하나에 대해 Ollama로 요약·흐름·키워드를 추출한다."""
    prompt = build_it_keyword_prompt(row)
    return ItKeywordResult(**_ollama_chat_json(prompt))


def _is_blank_series(series: pd.Series) -> pd.Series:
    """문자열 컬럼의 결측 또는 공백 여부를 반환한다."""
    empty_map = {value: pd.NA for value in AnalyzeItKeywordsConfig.CONTENT_EMPTY_PLACEHOLDERS}
    normalized = series.replace(empty_map)
    return normalized.isna() | normalized.astype(str).str.strip().eq("")


def _validate_required_columns(df: pd.DataFrame) -> None:
    """IC02 분석 필수 analysis 컬럼을 검증한다."""
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
    """analysis row에 crawling 관심도 메트릭을 붙인다."""
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
    """IC02 전용 키워드 처리 대상 row를 필터링한다."""
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
    """IC02 IT 뉴스 row의 `analysis.keywords`를 채운다."""
    df = get_analysis_data()
    _validate_required_columns(df)

    df = _filter_it_keyword_targets(df, overwrite=overwrite)
    if df.empty:
        logger.info(PostAnalysisErrors.ItKeywords.no_pending_rows())
        return

    if max_rows is not None and max_rows > 0:
        df = df.head(max_rows).copy()
        logger.info("IC02 IT 키워드 상한 적용: %s건 처리 (max_rows=%s)", len(df), max_rows)

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
                logger.info("IC02 IT 키워드 빈 결과로 제외 (crawling_id=%s)", crawling_id)
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

    merge_analysis_data(df.loc[success_indexes].copy())
    logger.info("IC02 IT 키워드 추출 완료 (%s건)", len(success_indexes))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s [%(name)s] %(message)s")
    analyze_it_keywords()
```

- [ ] **Step 5: Run IC02 orchestration tests**

Run:

```powershell
C:\Python314\python.exe -m pytest ai\post_analysis\tests\unit\test_l3_analyze_it_keywords_indirect.py -v
```

Expected: PASS.

- [ ] **Step 6: Run helper tests**

Run:

```powershell
C:\Python314\python.exe -m pytest ai\post_analysis\tests\unit\test_l0_it_keywords.py -v
```

Expected: PASS.

- [ ] **Step 7: Commit**

```powershell
git add ai\post_analysis\analyze_it_keywords.py ai\post_analysis\tests\conftest.py ai\post_analysis\tests\unit\test_l3_analyze_it_keywords_indirect.py
git commit -m "feat: add ic02 keyword analysis stage"
```

---

### Task 4: Wire IC02 Stage Into Pipeline

**Files:**
- Modify: `ai/post_analysis/pipeline.py`
- Modify: `ai/post_analysis/tests/unit/test_l3_run_pipeline_indirect.py`

- [ ] **Step 1: Update pipeline tests first**

Replace `ai/post_analysis/tests/unit/test_l3_run_pipeline_indirect.py` with this content:

```python
"""PA-L2/3-PLN: run_pipeline 간접 검증 (4단계 함수 patch)."""

from unittest.mock import MagicMock, patch

import pytest

from pipeline import run_pipeline


@patch("pipeline.analyze_it_keywords")
@patch("pipeline.analyze_keywords")
@patch("pipeline.analyze_sentimental")
@patch("pipeline.get_reviews")
def test_pa_l2_pln_001_invalid_max_rows(
    mock_gr: MagicMock,
    mock_as: MagicMock,
    mock_kw: MagicMock,
    mock_it_kw: MagicMock,
) -> None:
    """PA-L2-PLN-001 [실패]: max_rows<=0 이면 ValueError, 단계 함수 미호출."""
    with pytest.raises(ValueError, match="max_rows"):
        run_pipeline(max_rows=0)
    mock_gr.assert_not_called()
    mock_as.assert_not_called()
    mock_kw.assert_not_called()
    mock_it_kw.assert_not_called()


@patch("pipeline.analyze_it_keywords")
@patch("pipeline.analyze_keywords")
@patch("pipeline.analyze_sentimental")
@patch("pipeline.get_reviews")
def test_pa_l2_pln_002_step_order(
    mock_gr: MagicMock,
    mock_as: MagicMock,
    mock_kw: MagicMock,
    mock_it_kw: MagicMock,
) -> None:
    """PA-L2-PLN-002 [정상]: 기존 3단계 이후 IC02 키워드 단계 실행."""
    calls: list[str] = []

    mock_gr.side_effect = lambda: calls.append("gr")
    mock_as.side_effect = lambda: calls.append("as")
    mock_kw.side_effect = lambda max_rows=None: calls.append(f"kw:{max_rows}")
    mock_it_kw.side_effect = lambda max_rows=None, overwrite=False: calls.append(
        f"it_kw:{max_rows}:{overwrite}"
    )

    run_pipeline(max_rows=None)
    assert calls == ["gr", "as", "kw:None", "it_kw:None:False"]


@patch("pipeline.analyze_it_keywords")
@patch("pipeline.analyze_keywords")
@patch("pipeline.analyze_sentimental")
@patch("pipeline.get_reviews")
def test_pa_l2_pln_003_passes_max_rows_to_keywords(
    mock_gr: MagicMock,
    mock_as: MagicMock,
    mock_kw: MagicMock,
    mock_it_kw: MagicMock,
) -> None:
    """PA-L2-PLN-003 [정상]: max_rows는 기존 IC01 키워드에만 전달."""
    run_pipeline(max_rows=3)
    mock_kw.assert_called_once_with(max_rows=3)
    mock_it_kw.assert_called_once_with(max_rows=None, overwrite=False)


@patch("pipeline.analyze_it_keywords")
@patch("pipeline.analyze_keywords")
@patch("pipeline.analyze_sentimental")
@patch("pipeline.get_reviews")
def test_pa_l2_pln_004_passes_it_keyword_options(
    mock_gr: MagicMock,
    mock_as: MagicMock,
    mock_kw: MagicMock,
    mock_it_kw: MagicMock,
) -> None:
    """PA-L2-PLN-004 [정상]: IC02 키워드 옵션은 IC02 단계에만 전달."""
    run_pipeline(max_rows=2, it_keywords_max_rows=5, overwrite_it_keywords=True)
    mock_kw.assert_called_once_with(max_rows=2)
    mock_it_kw.assert_called_once_with(max_rows=5, overwrite=True)


@patch("pipeline.analyze_it_keywords")
@patch("pipeline.analyze_keywords")
@patch("pipeline.analyze_sentimental")
@patch("pipeline.get_reviews")
def test_pa_l2_pln_005_invalid_it_keywords_max_rows(
    mock_gr: MagicMock,
    mock_as: MagicMock,
    mock_kw: MagicMock,
    mock_it_kw: MagicMock,
) -> None:
    """PA-L2-PLN-005 [실패]: it_keywords_max_rows<=0 이면 단계 함수 미호출."""
    with pytest.raises(ValueError, match="max_rows"):
        run_pipeline(it_keywords_max_rows=0)
    mock_gr.assert_not_called()
    mock_as.assert_not_called()
    mock_kw.assert_not_called()
    mock_it_kw.assert_not_called()
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```powershell
C:\Python314\python.exe -m pytest ai\post_analysis\tests\unit\test_l3_run_pipeline_indirect.py -v
```

Expected: FAIL because `pipeline.analyze_it_keywords` is not imported and `run_pipeline` does not accept IC02 options.

- [ ] **Step 3: Update `pipeline.py` imports and signature**

Modify imports near the top:

```python
from analyze_it_keywords import analyze_it_keywords
from analyze_keywords import analyze_keywords
from analyze_sentimental import analyze_sentimental
```

Change `run_pipeline` signature:

```python
def run_pipeline(
    max_rows: int | None = None,
    it_keywords_max_rows: int | None = None,
    overwrite_it_keywords: bool = False,
) -> None:
```

Add validation after existing max_rows validation:

```python
    if it_keywords_max_rows is not None and it_keywords_max_rows <= 0:
        raise ValueError(PostAnalysisErrors.Pipeline.invalid_max_rows(it_keywords_max_rows))
```

Change `steps` to:

```python
    steps = (
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
            },
        ),
    )
```

- [ ] **Step 4: Update CLI args**

In `_parse_args`, add:

```python
    parser.add_argument(
        "--it-keywords-max-rows",
        type=int,
        default=None,
        help="IC02 IT 키워드 추출 상한 (미지정 시 제한 없음)",
    )
    parser.add_argument(
        "--overwrite-it-keywords",
        action="store_true",
        help="기존 IC02 keywords도 재생성",
    )
```

At the bottom, call:

```python
    run_pipeline(
        max_rows=args.max_rows,
        it_keywords_max_rows=args.it_keywords_max_rows,
        overwrite_it_keywords=args.overwrite_it_keywords,
    )
```

- [ ] **Step 5: Run pipeline tests**

Run:

```powershell
C:\Python314\python.exe -m pytest ai\post_analysis\tests\unit\test_l3_run_pipeline_indirect.py -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

```powershell
git add ai\post_analysis\pipeline.py ai\post_analysis\tests\unit\test_l3_run_pipeline_indirect.py
git commit -m "feat: wire ic02 keyword stage into pipeline"
```

---

### Task 5: Focused Verification

**Files:**
- Verify only.

- [ ] **Step 1: Run IC02-focused tests**

Run:

```powershell
C:\Python314\python.exe -m pytest ai\post_analysis\tests\unit\test_l0_it_keywords.py ai\post_analysis\tests\unit\test_l3_analyze_it_keywords_indirect.py ai\post_analysis\tests\unit\test_l3_run_pipeline_indirect.py -v
```

Expected: PASS.

- [ ] **Step 2: Run existing IC01 guard tests**

Run:

```powershell
C:\Python314\python.exe -m pytest ai\post_analysis\tests\unit\test_l2_analyze_sentimental_indirect.py ai\post_analysis\tests\unit\test_l3_analyze_keywords_bert_indirect.py -v
```

Expected: PASS. This confirms existing IC01 sentiment and BERT keyword behavior remains intact.

- [ ] **Step 3: Run full post_analysis test suite**

Run:

```powershell
C:\Python314\python.exe -m pytest ai\post_analysis -v
```

Expected: PASS. Merge guard remains active and no live DB writes occur.

- [ ] **Step 4: Inspect git diff for scope**

Run:

```powershell
git diff --stat HEAD
```

Expected: Only `ai/post_analysis` files are changed after implementation commits. There must be no changes under `etl/meal`, `etl/it_news`, `ai/postmake_pipeline`, `database`, or DB schema files.

- [ ] **Step 5: Final commit if verification required edits**

If verification caused any small fixes, commit them:

```powershell
git add ai\post_analysis
git commit -m "test: verify ic02 keyword analysis"
```

If no files changed, do not create an empty commit.

---

## Self-Review Checklist

- Spec coverage:
  - IC02-only module: Task 2 and Task 3.
  - Empty-only default and overwrite option: Task 3 tests and implementation.
  - Summary/flow/interest context: Task 2 prompt/model tests and Task 3 implementation.
  - Ollama `gemma4:26b`: Task 1 config and Task 2 env override test.
  - Existing IC01 untouched: Scope Guard and Task 5 IC01 tests.
  - Pipeline final step and CLI flags: Task 4.
  - No DB schema or downstream changes: Scope Guard and Task 5 diff check.
- Marker scan: no unresolved implementation markers are present.
- Type consistency:
  - `analyze_it_keywords(max_rows: int | None = None, overwrite: bool = False)` is used consistently.
  - `ItKeywordResult.summary`, `flow`, `interest_label`, `keywords` are used consistently.
  - `AnalyzeItKeywordsConfig` constants match tests and implementation snippets.
