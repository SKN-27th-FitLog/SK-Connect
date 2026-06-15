# IC02 Company Sentiment Keywords Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace slow IC02 LLM keyword extraction with deterministic company/company-type keywords and IC02 title sentiment storage.

**Architecture:** Keep the change inside `ai/post_analysis` IC02 code. Add a small IT company registry module, make `analyze_it_keywords` orchestrate company matching and `BertTokenizer.predict_sentiment(title)`, and update only the IC02 target SQL contract to fetch rows missing `sentimental` or `score`.

**Tech Stack:** Python, pandas, pytest, existing `BertTokenizer`, existing PostgreSQL merge helper.

---

## File Structure

- Modify: `docs/superpowers/specs/2026-06-09-ic02-company-sentiment-keywords-design.md`
  - Align log policy with error-focused operation: no normal progress, row success, payload, or INFO batch summary logs.
- Create: `ai/post_analysis/common/it_company_registry.py`
  - Own the deterministic IC02 company registry and matching logic.
- Modify: `ai/post_analysis/analyze_it_keywords.py`
  - Remove active Ollama/LLM selector, candidate scoring, progress-bar, and summary-content update behavior.
  - Keep public function name `analyze_it_keywords` for pipeline compatibility.
  - Store company/type keywords and title sentiment/score through `merge_analysis_data`.
- Modify: `ai/post_analysis/postgresql/run_query.py`
  - Change IC02 target query from missing `keywords` to missing `sentimental` or `score`.
  - Select `sentimental` and `score`; do not join crawling metrics for IC02 company/sentiment processing.
- Delete: `ai/post_analysis/common/it_keyword_candidates.py`
  - Remove stale IC02 candidate extraction helper that belonged to the old LLM keyword flow.
- Modify: `ai/post_analysis/common/constant.py`
  - Keep only IC02 company/sentiment settings still used by the new path.
- Modify: `ai/post_analysis/tests/unit/test_l0_it_keywords.py`
  - Replace LLM/prompt/candidate tests with deterministic company registry and keyword formatting tests.
- Modify: `ai/post_analysis/tests/unit/test_l2_it_keyword_target_query.py`
  - Update SQL contract tests for `sentimental`/`score` pending rows.
- Modify: `ai/post_analysis/tests/unit/test_l3_analyze_it_keywords_indirect.py`
  - Update orchestration tests for company matching, sentiment injection, merge columns, no Ollama call, no tqdm progress, and error-only normal logging.
- Modify: `ai/post_analysis/benchmark_it_keywords.py`
  - Remove stale LLM selector benchmark imports and full JSON payload printing.
- Modify: `ai/post_analysis/tests/unit/test_l2_it_keyword_benchmark.py`
  - Re-scope the benchmark helper to company registry match counts.
- Do not modify: `ai/post_analysis/analyze_sentimental.py`, `ai/post_analysis/analyze_keywords.py`, `ai/post_analysis/analyze_keywords_by_llm.py`, `etl/*`, `kag/*`, DB schema files.

---

### Task 1: Document Log Policy Alignment

**Files:**
- Modify: `docs/superpowers/specs/2026-06-09-ic02-company-sentiment-keywords-design.md`

- [ ] **Step 1: Verify spec log policy**

The spec must say the default IC02 run does not write normal progress logs, row success logs, result payload logs, or normal INFO batch summaries.

Expected lines:

```markdown
AWS 운영에서는 CloudWatch 로그 비용과 노이즈를 줄이기 위해 row별 성공 로그, 진행도 로그, 결과 payload 로그를 남기지 않는다.

`INFO`에는 기본적으로 IC02 처리 진행도나 정상 종료 요약을 남기지 않는다.

`DEBUG`에만 batch 요약과 row별 상세를 허용한다.

정상 batch summary 로그는 `INFO`로 남기지 않는다.
```

- [ ] **Step 2: Run document diff check**

Run:

```powershell
git diff -- docs\superpowers\specs\2026-06-09-ic02-company-sentiment-keywords-design.md
```

Expected: diff only changes the log policy and related test criterion.

---

### Task 2: Write RED Tests For Company Registry

**Files:**
- Create: `ai/post_analysis/common/it_company_registry.py`
- Modify: `ai/post_analysis/tests/unit/test_l0_it_keywords.py`

- [ ] **Step 1: Replace old L0 test imports**

Use these imports at the top of `test_l0_it_keywords.py`:

```python
from common.it_company_registry import (
    build_company_keyword_values,
    match_it_companies,
)
from analyze_it_keywords import normalize_it_keywords
```

- [ ] **Step 2: Add failing company matching tests**

Add these tests:

```python
def test_pa_l0_itkw_001_company_registry_matches_alias_case_insensitive() -> None:
    matches = match_it_companies(
        title="OpenAI and NVIDIA announce new AI infrastructure",
        content="chatgpt 개발사와 nvidia가 GPU 생태계를 확장했다.",
    )

    assert [company.canonical_name for company in matches] == ["OpenAI", "NVIDIA"]
    assert [company.company_type for company in matches] == ["ai_company", "semiconductor"]


def test_pa_l0_itkw_002_company_keywords_flatten_name_and_type_once() -> None:
    matches = match_it_companies(
        title="OpenAI OpenAI",
        content="ChatGPT 개발사 OpenAI가 새 모델을 공개했다.",
    )

    assert build_company_keyword_values(matches) == ["OpenAI", "ai_company"]
    assert normalize_it_keywords(build_company_keyword_values(matches)) == "#OpenAI#ai_company"


def test_pa_l0_itkw_003_company_registry_keeps_document_priority() -> None:
    matches = match_it_companies(
        title="NVIDIA and OpenAI expand model training",
        content="Microsoft also joined the infrastructure update.",
    )

    assert [company.canonical_name for company in matches] == [
        "OpenAI",
        "Microsoft",
        "NVIDIA",
    ]


def test_pa_l0_itkw_004_company_registry_returns_empty_for_unknown_text() -> None:
    assert match_it_companies(title="새로운 오픈소스 릴리스", content="회사명 언급 없음") == []
```

- [ ] **Step 3: Verify RED**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest ai\post_analysis\tests\unit\test_l0_it_keywords.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'common.it_company_registry'`.

---

### Task 3: Implement Company Registry

**Files:**
- Create: `ai/post_analysis/common/it_company_registry.py`

- [ ] **Step 1: Add deterministic registry module**

Create `it_company_registry.py` with:

```python
"""IC02 IT 회사 사전과 deterministic 매칭 로직."""

from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class ItCompany:
    """IC02 회사 키워드 저장에 필요한 최소 회사 정보."""

    canonical_name: str
    company_type: str
    aliases: tuple[str, ...]


IT_COMPANIES: tuple[ItCompany, ...] = (
    ItCompany("OpenAI", "ai_company", ("openai", "chatgpt 개발사")),
    ItCompany("Anthropic", "ai_company", ("anthropic", "claude 개발사")),
    ItCompany("Google", "bigtech", ("google", "구글", "alphabet")),
    ItCompany("Microsoft", "bigtech", ("microsoft", "ms", "마이크로소프트")),
    ItCompany("Apple", "bigtech", ("apple", "애플")),
    ItCompany("NVIDIA", "semiconductor", ("nvidia", "엔비디아")),
    ItCompany("Samsung", "semiconductor", ("samsung", "삼성", "삼성전자")),
)


def _text_or_empty(value: object) -> str:
    if value is None:
        return ""
    return str(value)


def _is_ascii_word_alias(alias: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9.+_-]*", alias))


def _contains_alias(text: str, alias: str) -> bool:
    if not alias:
        return False
    if _is_ascii_word_alias(alias):
        pattern = rf"(?<![A-Za-z0-9]){re.escape(alias)}(?![A-Za-z0-9])"
        return re.search(pattern, text, flags=re.IGNORECASE) is not None
    return alias.casefold() in text.casefold()


def match_it_companies(title: object, content: object) -> list[ItCompany]:
    """title/content에서 회사 사전 순서대로 매칭된 회사를 반환한다."""
    text = f"{_text_or_empty(title)}\n{_text_or_empty(content)}"
    matches: list[ItCompany] = []
    for company in IT_COMPANIES:
        if any(_contains_alias(text, alias) for alias in company.aliases):
            matches.append(company)
    return matches


def build_company_keyword_values(companies: list[ItCompany]) -> list[str]:
    """회사명과 회사 분류를 `#회사명#분류` 저장 순서에 맞는 flat list로 만든다."""
    values: list[str] = []
    for company in companies:
        values.extend([company.canonical_name, company.company_type])
    return values
```

- [ ] **Step 2: Verify GREEN**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest ai\post_analysis\tests\unit\test_l0_it_keywords.py -v
```

Expected: PASS for the company registry tests.

---

### Task 4: Write RED Tests For IC02 Target Query

**Files:**
- Modify: `ai/post_analysis/tests/unit/test_l2_it_keyword_target_query.py`
- Modify: `ai/post_analysis/postgresql/run_query.py`

- [ ] **Step 1: Update cursor columns in test helper**

The helper cursor description must be:

```python
cursor.description = [
    SimpleNamespace(name=AnalysisColumn.CRAWLING_ID.value),
    SimpleNamespace(name=AnalysisColumn.TITLE.value),
    SimpleNamespace(name=AnalysisColumn.CONTENT.value),
    SimpleNamespace(name=AnalysisColumn.KEYWORDS.value),
    SimpleNamespace(name=AnalysisColumn.INFORMATION_CD.value),
    SimpleNamespace(name=AnalysisColumn.SENTIMENTAL.value),
    SimpleNamespace(name=AnalysisColumn.SCORE.value),
]
```

- [ ] **Step 2: Update pending query assertions**

The pending query test must assert:

```python
assert "FROM analysis AS a" in sql
assert "LEFT JOIN crawling AS c" not in sql
assert "a.information_cd = %s" in sql
assert "(a.sentimental IS NULL OR BTRIM(a.sentimental) = '')" in sql
assert "a.score IS NULL" in sql
assert "BTRIM(a.keywords)" not in sql
assert "LIMIT %s" in sql
assert CodeTable.INFORMATION_IT_INFO.value in params
assert 5 in params
assert list(df.columns) == [
    AnalysisColumn.CRAWLING_ID.value,
    AnalysisColumn.TITLE.value,
    AnalysisColumn.CONTENT.value,
    AnalysisColumn.KEYWORDS.value,
    AnalysisColumn.INFORMATION_CD.value,
    AnalysisColumn.SENTIMENTAL.value,
    AnalysisColumn.SCORE.value,
]
```

- [ ] **Step 3: Update overwrite query assertions**

The overwrite test must assert:

```python
assert "a.information_cd = %s" in sql
assert "a.sentimental IS NULL" not in sql
assert "a.score IS NULL" not in sql
assert "BTRIM(a.keywords)" not in sql
assert "LEFT JOIN crawling AS c" not in sql
assert "LIMIT %s" not in sql
assert CodeTable.INFORMATION_IT_INFO.value in params
```

- [ ] **Step 4: Verify RED**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest ai\post_analysis\tests\unit\test_l2_it_keyword_target_query.py -v
```

Expected: FAIL because the query still filters missing `keywords` and joins crawling metrics.

---

### Task 5: Implement IC02 Target Query

**Files:**
- Modify: `ai/post_analysis/postgresql/run_query.py`

- [ ] **Step 1: Change query filter and selected columns**

In `get_it_keyword_target_data`, replace keyword pending logic with:

```python
pending_condition = ""
if not overwrite:
    pending_condition = (
        "\n      AND ("
        "\n        (a.sentimental IS NULL OR BTRIM(a.sentimental) = '')"
        "\n        OR a.score IS NULL"
        "\n      )"
    )
```

The SELECT must include:

```sql
SELECT
    a.crawling_id,
    a.title,
    a.content,
    a.keywords,
    a.information_cd,
    a.sentimental,
    a.score
FROM analysis AS a
WHERE a.information_cd = %s
  AND (({valid_title_sql}) OR ({valid_content_sql})){pending_condition}
ORDER BY a.crawling_id{limit_sql}
```

- [ ] **Step 2: Verify GREEN**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest ai\post_analysis\tests\unit\test_l2_it_keyword_target_query.py -v
```

Expected: PASS.

---

### Task 6: Write RED Tests For IC02 Orchestration

**Files:**
- Modify: `ai/post_analysis/tests/unit/test_l3_analyze_it_keywords_indirect.py`
- Modify: `ai/post_analysis/analyze_it_keywords.py`

- [ ] **Step 1: Replace old orchestration tests**

Use a compact test module that imports:

```python
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from analyze_it_keywords import analyze_it_keywords
from common.constant import AnalysisColumn, CodeTable
```

- [ ] **Step 2: Add IC02 fixture**

Use this fixture helper:

```python
def _analysis_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            AnalysisColumn.CRAWLING_ID.value: [101, 102, 103, 104],
            AnalysisColumn.TITLE.value: [
                "OpenAI updates ChatGPT",
                "Meal B",
                "NVIDIA ships GPU update",
                "",
            ],
            AnalysisColumn.CONTENT.value: [
                "ChatGPT 개발사가 새 모델을 공개했다.",
                "meal review",
                "NVIDIA GPU platform update",
                "",
            ],
            AnalysisColumn.KEYWORDS.value: [pd.NA, pd.NA, "#existing", pd.NA],
            AnalysisColumn.INFORMATION_CD.value: [
                CodeTable.INFORMATION_IT_INFO.value,
                CodeTable.INFORMATION_RESTAURANT.value,
                CodeTable.INFORMATION_IT_INFO.value,
                CodeTable.INFORMATION_IT_INFO.value,
            ],
            AnalysisColumn.SENTIMENTAL.value: [pd.NA, pd.NA, "positive", pd.NA],
            AnalysisColumn.SCORE.value: [pd.NA, pd.NA, 0.8, pd.NA],
        }
    )
```

- [ ] **Step 3: Add default run test**

```python
@patch("analyze_it_keywords.merge_analysis_data")
@patch("analyze_it_keywords.BertTokenizer")
@patch("analyze_it_keywords.get_it_keyword_target_data")
def test_pa_l3_itkw_001_processes_ic02_missing_sentiment_only(
    mock_get_targets: MagicMock,
    mock_tokenizer_cls: MagicMock,
    mock_merge: MagicMock,
) -> None:
    mock_get_targets.return_value = _analysis_df()
    tokenizer = MagicMock()
    tokenizer.predict_sentiment.return_value = {"sentimental": "positive", "score": 0.91}
    mock_tokenizer_cls.return_value = tokenizer

    analyze_it_keywords()

    tokenizer.predict_sentiment.assert_called_once_with("OpenAI updates ChatGPT")
    mock_merge.assert_called_once()
    df = mock_merge.call_args[0][0]
    assert list(df.columns) == [
        AnalysisColumn.CRAWLING_ID.value,
        AnalysisColumn.KEYWORDS.value,
        AnalysisColumn.SENTIMENTAL.value,
        AnalysisColumn.SCORE.value,
    ]
    assert df[AnalysisColumn.CRAWLING_ID.value].tolist() == [101]
    assert df[AnalysisColumn.KEYWORDS.value].iloc[0] == "#OpenAI#ai_company"
    assert df[AnalysisColumn.SENTIMENTAL.value].iloc[0] == "positive"
    assert df[AnalysisColumn.SCORE.value].iloc[0] == 0.91
```

- [ ] **Step 4: Add overwrite and no-company tests**

```python
@patch("analyze_it_keywords.merge_analysis_data")
@patch("analyze_it_keywords.BertTokenizer")
@patch("analyze_it_keywords.get_it_keyword_target_data")
def test_pa_l3_itkw_002_overwrite_reprocesses_valid_ic02_rows(
    mock_get_targets: MagicMock,
    mock_tokenizer_cls: MagicMock,
    mock_merge: MagicMock,
) -> None:
    mock_get_targets.return_value = _analysis_df()
    tokenizer = MagicMock()
    tokenizer.predict_sentiment.return_value = {"sentimental": "negative", "score": 0.77}
    mock_tokenizer_cls.return_value = tokenizer

    analyze_it_keywords(overwrite=True)

    assert tokenizer.predict_sentiment.call_count == 2
    df = mock_merge.call_args[0][0]
    assert df[AnalysisColumn.CRAWLING_ID.value].tolist() == [101, 103]
    assert df[AnalysisColumn.KEYWORDS.value].tolist() == [
        "#OpenAI#ai_company",
        "#NVIDIA#semiconductor",
    ]


@patch("analyze_it_keywords.merge_analysis_data")
@patch("analyze_it_keywords.BertTokenizer")
@patch("analyze_it_keywords.get_it_keyword_target_data")
def test_pa_l3_itkw_003_unmatched_company_preserves_existing_keywords(
    mock_get_targets: MagicMock,
    mock_tokenizer_cls: MagicMock,
    mock_merge: MagicMock,
) -> None:
    mock_get_targets.return_value = pd.DataFrame(
        {
            AnalysisColumn.CRAWLING_ID.value: [201],
            AnalysisColumn.TITLE.value: ["Open source release"],
            AnalysisColumn.CONTENT.value: ["No registered company name"],
            AnalysisColumn.KEYWORDS.value: ["#existing"],
            AnalysisColumn.INFORMATION_CD.value: [CodeTable.INFORMATION_IT_INFO.value],
            AnalysisColumn.SENTIMENTAL.value: [pd.NA],
            AnalysisColumn.SCORE.value: [pd.NA],
        }
    )
    tokenizer = MagicMock()
    tokenizer.predict_sentiment.return_value = {"sentimental": "positive", "score": 0.66}
    mock_tokenizer_cls.return_value = tokenizer

    analyze_it_keywords()

    df = mock_merge.call_args[0][0]
    assert df[AnalysisColumn.KEYWORDS.value].iloc[0] is None
    assert df[AnalysisColumn.SENTIMENTAL.value].iloc[0] == "positive"
```

- [ ] **Step 5: Add no INFO/progress and failure tests**

```python
@patch("analyze_it_keywords.tqdm", create=True)
@patch("analyze_it_keywords.merge_analysis_data")
@patch("analyze_it_keywords.BertTokenizer")
@patch("analyze_it_keywords.get_it_keyword_target_data")
def test_pa_l3_itkw_004_does_not_use_progress_bar(
    mock_get_targets: MagicMock,
    mock_tokenizer_cls: MagicMock,
    mock_merge: MagicMock,
    mock_tqdm: MagicMock,
) -> None:
    mock_get_targets.return_value = _analysis_df()
    tokenizer = MagicMock()
    tokenizer.predict_sentiment.return_value = {"sentimental": "positive", "score": 0.9}
    mock_tokenizer_cls.return_value = tokenizer

    analyze_it_keywords()

    mock_tqdm.assert_not_called()


@patch("analyze_it_keywords.merge_analysis_data")
@patch("analyze_it_keywords.BertTokenizer")
@patch("analyze_it_keywords.get_it_keyword_target_data")
def test_pa_l3_itkw_005_normal_success_does_not_log_info(
    mock_get_targets: MagicMock,
    mock_tokenizer_cls: MagicMock,
    mock_merge: MagicMock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    mock_get_targets.return_value = _analysis_df()
    tokenizer = MagicMock()
    tokenizer.predict_sentiment.return_value = {"sentimental": "positive", "score": 0.9}
    mock_tokenizer_cls.return_value = tokenizer

    analyze_it_keywords()

    assert [record for record in caplog.records if record.levelname == "INFO"] == []


@patch("analyze_it_keywords.merge_analysis_data")
@patch("analyze_it_keywords.BertTokenizer")
@patch("analyze_it_keywords.get_it_keyword_target_data")
def test_pa_l3_itkw_006_row_failure_merges_successes_only(
    mock_get_targets: MagicMock,
    mock_tokenizer_cls: MagicMock,
    mock_merge: MagicMock,
) -> None:
    mock_get_targets.return_value = pd.DataFrame(
        {
            AnalysisColumn.CRAWLING_ID.value: [301, 302],
            AnalysisColumn.TITLE.value: ["OpenAI update", "NVIDIA update"],
            AnalysisColumn.CONTENT.value: ["OpenAI content", "NVIDIA content"],
            AnalysisColumn.KEYWORDS.value: [pd.NA, pd.NA],
            AnalysisColumn.INFORMATION_CD.value: [CodeTable.INFORMATION_IT_INFO.value] * 2,
            AnalysisColumn.SENTIMENTAL.value: [pd.NA, pd.NA],
            AnalysisColumn.SCORE.value: [pd.NA, pd.NA],
        }
    )
    tokenizer = MagicMock()
    tokenizer.predict_sentiment.side_effect = [
        RuntimeError("model failed"),
        {"sentimental": "negative", "score": 0.7},
    ]
    mock_tokenizer_cls.return_value = tokenizer

    analyze_it_keywords()

    df = mock_merge.call_args[0][0]
    assert df[AnalysisColumn.CRAWLING_ID.value].tolist() == [302]
    assert df[AnalysisColumn.KEYWORDS.value].iloc[0] == "#NVIDIA#semiconductor"
```

- [ ] **Step 6: Verify RED**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest ai\post_analysis\tests\unit\test_l3_analyze_it_keywords_indirect.py -v
```

Expected: FAIL because the current implementation still calls the old LLM keyword path, progress wrapper, and keyword-missing filter behavior.

---

### Task 7: Implement IC02 Company/Sentiment Orchestration

**Files:**
- Modify: `ai/post_analysis/analyze_it_keywords.py`

- [ ] **Step 1: Replace active LLM imports with company and sentiment imports**

Use:

```python
from dataclasses import dataclass
import html
import logging
import re

import pandas as pd

import common.env  # noqa: F401 - DB 환경변수 로드
from common.bert_tokenizer import BertTokenizer
from common.constant import AnalysisColumn, AnalyzeItKeywordsConfig, CodeTable, SentimentResultKey
from common.errors import PostAnalysisErrors
from common.it_company_registry import build_company_keyword_values, match_it_companies
from postgresql.run_query import get_it_keyword_target_data, merge_analysis_data
```

- [ ] **Step 2: Use focused result dataclass**

```python
@dataclass(frozen=True)
class ItKeywordAnalysisResult:
    """IC02 회사 키워드와 제목 감성 처리 결과."""

    keywords: str | None
    sentimental: str
    score: float
```

- [ ] **Step 3: Keep text and keyword normalization helpers**

Keep `_text_or_empty`, `_is_blank_series`, and `normalize_it_keywords`. The keyword normalizer remains the downstream `#` format compatibility point.

- [ ] **Step 4: Add row analyzer**

```python
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
```

- [ ] **Step 5: Change required columns**

```python
required = (
    AnalysisColumn.CRAWLING_ID.value,
    AnalysisColumn.TITLE.value,
    AnalysisColumn.CONTENT.value,
    AnalysisColumn.KEYWORDS.value,
    AnalysisColumn.INFORMATION_CD.value,
    AnalysisColumn.SENTIMENTAL.value,
    AnalysisColumn.SCORE.value,
)
```

- [ ] **Step 6: Change target filtering**

```python
if overwrite:
    return df
missing_sentiment = _is_blank_series(df[AnalysisColumn.SENTIMENTAL.value])
missing_score = df[AnalysisColumn.SCORE.value].isna()
return df[missing_sentiment | missing_score].copy()
```

- [ ] **Step 7: Build merge payload without normal INFO logs**

```python
tokenizer = BertTokenizer()
updates: list[dict[str, object]] = []
for index, row in df.iterrows():
    crawling_id = row[AnalysisColumn.CRAWLING_ID.value]
    try:
        result = analyze_it_keyword_row(row, tokenizer=tokenizer)
    except Exception:
        logger.exception(PostAnalysisErrors.ItKeywords.row_processing_failed(), crawling_id, index)
        continue
    updates.append(
        {
            AnalysisColumn.CRAWLING_ID.value: crawling_id,
            AnalysisColumn.KEYWORDS.value: result.keywords,
            AnalysisColumn.SENTIMENTAL.value: result.sentimental,
            AnalysisColumn.SCORE.value: result.score,
        }
    )

if not updates:
    logger.debug(PostAnalysisErrors.ItKeywords.no_successful_rows())
    return
merge_analysis_data(pd.DataFrame(updates))
logger.debug("IC02 company/sentiment analysis completed rows=%s", len(updates))
```

- [ ] **Step 8: Verify GREEN**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest ai\post_analysis\tests\unit\test_l3_analyze_it_keywords_indirect.py -v
```

Expected: PASS.

---

### Task 8: Remove Stale IT LLM Benchmark Coupling

**Files:**
- Modify: `ai/post_analysis/benchmark_it_keywords.py`
- Modify: `ai/post_analysis/tests/unit/test_l2_it_keyword_benchmark.py`

- [ ] **Step 1: Replace benchmark test with company matching report test**

Use this assertion shape:

```python
report = build_it_keyword_benchmark_report(rows)

assert report["sample_size"] == 2
assert report["company_matched_count"] == 1
assert report["company_unmatched_count"] == 1
assert report["rows"][0]["matched_companies"] == ["OpenAI"]
assert "llm_selector" not in report
```

- [ ] **Step 2: Replace benchmark implementation**

`build_it_keyword_benchmark_report` must use `match_it_companies` and must not import `preprocess_it_content`, `evaluate_it_keyword_candidate_confidence`, or `extract_it_keyword_candidates`.

- [ ] **Step 3: Remove full payload print**

`main()` must print only generated report paths:

```python
print(f"JSON={json_path}")
print(f"MARKDOWN={md_path}")
```

- [ ] **Step 4: Verify GREEN**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest ai\post_analysis\tests\unit\test_l2_it_keyword_benchmark.py -v
```

Expected: PASS.

---

### Task 9: Run Focused Regression

**Files:**
- Verify only.

- [ ] **Step 1: Run IT focused tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest ai\post_analysis\tests\unit\test_l0_it_keywords.py ai\post_analysis\tests\unit\test_l2_it_keyword_target_query.py ai\post_analysis\tests\unit\test_l3_analyze_it_keywords_indirect.py ai\post_analysis\tests\unit\test_l2_it_keyword_benchmark.py -v
```

Expected: PASS.

- [ ] **Step 2: Run IC01 guard tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest ai\post_analysis\tests\unit\test_l2_analyze_sentimental_indirect.py ai\post_analysis\tests\unit\test_l3_analyze_keywords_bert_indirect.py -v
```

Expected: PASS, proving IC01 sentiment and keyword exclusion contracts still hold.

- [ ] **Step 3: Run diff check**

Run:

```powershell
git diff --check
```

Expected: PASS with no whitespace errors. CRLF warnings are acceptable on this workspace.

---

## Self-Review

- Spec coverage:
  - LLM/Ollama removal: Task 7 removes active LLM calls from `analyze_it_keywords`.
  - Old candidate extraction removal: File structure deletes `common/it_keyword_candidates.py` and trims stale IC02 config.
  - Company/type keywords only: Tasks 2, 3, 6, 7 cover registry, order, dedupe, and merge payload.
  - IC02 title sentiment: Tasks 6 and 7 call `BertTokenizer.predict_sentiment(title)` and store existing `sentimental`/`score` columns.
  - IT-only scope: File structure excludes IC01 modules, KAG, ETL, DB schema, and postmake pipeline.
  - Error-focused logging: Task 1 and Task 6 assert no normal INFO/progress logs.
  - AWS cost reduction: Task 5 removes crawling metric join and Task 7 removes Ollama/progress.
- Placeholder scan:
  - This plan contains concrete file paths, test code, implementation snippets, and verification commands.
- Type consistency:
  - `ItKeywordAnalysisResult.keywords` is `str | None`, matching `merge_analysis_data` COALESCE behavior.
  - Sentiment keys use `SentimentResultKey.SENTIMENTAL.value` and `SentimentResultKey.SCORE.value`.
  - DataFrame column constants are all from `AnalysisColumn`.
