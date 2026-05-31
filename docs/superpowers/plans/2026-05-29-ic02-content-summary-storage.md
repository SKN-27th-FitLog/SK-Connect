# IC02 Content Summary Storage Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Store IC02 keyword extraction summaries inside `analysis.content` as `[본문]` and `[요약]` blocks without changing the DB schema.

**Architecture:** Keep the change inside `ai/post_analysis/analyze_it_keywords.py`. Add pure helpers for extracting the original body and formatting enriched content, then include `content` in the IC02 success merge payload only when `ItKeywordResult.summary` is non-empty.

**Tech Stack:** Python, pandas, pytest, existing `merge_analysis_data` PostgreSQL merge utility.

---

### Task 1: Pure Content Formatting Helpers

**Files:**
- Modify: `ai/post_analysis/analyze_it_keywords.py`
- Test: `ai/post_analysis/tests/unit/test_l0_it_keywords.py`

- [ ] **Step 1: Write failing tests**

Add tests that import `build_summary_enriched_content` and `extract_original_content`.

```python
def test_pa_l0_itkw_028_build_summary_enriched_content_formats_body_and_summary() -> None:
    result = build_summary_enriched_content("원문 본문", "요약 문장")

    assert result == "[본문]\n원문 본문\n\n[요약]\n요약 문장"


def test_pa_l0_itkw_029_build_summary_enriched_content_does_not_duplicate_existing_summary() -> None:
    content = "[본문]\n원문 본문\n\n[요약]\n이전 요약"

    result = build_summary_enriched_content(content, "새 요약")

    assert result == "[본문]\n원문 본문\n\n[요약]\n새 요약"


def test_pa_l0_itkw_030_build_summary_enriched_content_returns_none_for_blank_summary() -> None:
    assert build_summary_enriched_content("원문 본문", "   ") is None
```

- [ ] **Step 2: Run failing tests**

Run:

```powershell
C:\dev\Project\SK-Connect\.venv\Scripts\python.exe -m pytest tests\unit\test_l0_it_keywords.py::test_pa_l0_itkw_028_build_summary_enriched_content_formats_body_and_summary tests\unit\test_l0_it_keywords.py::test_pa_l0_itkw_029_build_summary_enriched_content_does_not_duplicate_existing_summary tests\unit\test_l0_it_keywords.py::test_pa_l0_itkw_030_build_summary_enriched_content_returns_none_for_blank_summary -v
```

Expected: FAIL because the helper functions do not exist.

- [ ] **Step 3: Implement helpers**

Add constants for `[본문]` and `[요약]`, then implement:

```python
CONTENT_BODY_MARKER = "[본문]"
CONTENT_SUMMARY_MARKER = "[요약]"


def extract_original_content(content: object) -> str:
    text = _text_or_empty(content)
    if text.startswith(CONTENT_BODY_MARKER) and CONTENT_SUMMARY_MARKER in text:
        body = text[len(CONTENT_BODY_MARKER):].split(CONTENT_SUMMARY_MARKER, 1)[0]
        return body.strip()
    return text


def build_summary_enriched_content(content: object, summary: object) -> str | None:
    body = extract_original_content(content)
    summary_text = _text_or_empty(summary)
    if not summary_text:
        return None
    return f"{CONTENT_BODY_MARKER}\n{body}\n\n{CONTENT_SUMMARY_MARKER}\n{summary_text}"
```

- [ ] **Step 4: Run tests**

Run the same command from Step 2. Expected: PASS.

### Task 2: Merge Content With Keywords

**Files:**
- Modify: `ai/post_analysis/analyze_it_keywords.py`
- Test: `ai/post_analysis/tests/unit/test_l3_analyze_it_keywords_indirect.py`

- [ ] **Step 1: Update orchestration tests**

Change the first IC02 orchestration test to expect merge columns:

```python
assert list(df.columns) == [
    AnalysisColumn.CRAWLING_ID.value,
    AnalysisColumn.CONTENT.value,
    AnalysisColumn.KEYWORDS.value,
]
assert df[AnalysisColumn.CONTENT.value].iloc[0] == (
    "[본문]\nPyTorch update\n\n[요약]\nsummary"
)
```

Add one test where `ItKeywordResult.summary` is blank and merge payload contains only `crawling_id`, `keywords`.

- [ ] **Step 2: Run failing tests**

Run:

```powershell
C:\dev\Project\SK-Connect\.venv\Scripts\python.exe -m pytest tests\unit\test_l3_analyze_it_keywords_indirect.py::test_pa_l3_itkw_001_processes_ic02_missing_keywords_only -v
```

Expected: FAIL because content is not included in the merge payload yet.

- [ ] **Step 3: Implement merge payload change**

Inside `analyze_it_keywords`, when a row succeeds:

```python
enriched_content = build_summary_enriched_content(
    row.get(AnalysisColumn.CONTENT.value),
    result.summary,
)
if enriched_content is not None:
    df.at[index, AnalysisColumn.CONTENT.value] = enriched_content
```

At merge time, include `content` only if at least one successful row has enriched content:

```python
merge_columns = [id_col]
if content_col in df.columns and any(index in content_update_indexes for index in success_indexes):
    merge_columns.append(content_col)
merge_columns.append(kw_col)
```

- [ ] **Step 4: Run focused tests**

Run:

```powershell
C:\dev\Project\SK-Connect\.venv\Scripts\python.exe -m pytest tests\unit\test_l0_it_keywords.py tests\unit\test_l3_analyze_it_keywords_indirect.py -v
```

Expected: PASS.

### Task 3: Final Verification

**Files:**
- Verify: `ai/post_analysis`

- [ ] **Step 1: Run post_analysis test suite**

Run:

```powershell
C:\dev\Project\SK-Connect\.venv\Scripts\python.exe -m pytest -v
```

Working directory:

```text
C:\dev\Project\SK-Connect\ai\post_analysis
```

Expected: PASS, with readonly and slow markers excluded by `pytest.ini`.

- [ ] **Step 2: Report**

Report Root Cause, Change, Verification, and Remaining Risk. Do not run `ai/postmake_pipeline`.
