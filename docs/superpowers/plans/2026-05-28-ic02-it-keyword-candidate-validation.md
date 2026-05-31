# IC02 IT Keyword Candidate Validation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prevent IC02 keyword extraction from storing LLM-generated keywords that are not grounded in the source title/content.

**Architecture:** Add a pure KiWi-backed candidate extraction module under `ai/post_analysis/common`, pass ranked candidates into the IC02 LLM prompt, and filter LLM output against those candidates before DB merge. Keep IC01 analysis, ETL, postmake, and DB schema untouched.

**Tech Stack:** Python, pandas, pydantic, kiwipiepy, pytest, existing Ollama HTTP client.

---

## File Responsibilities

- Create `ai/post_analysis/common/it_keyword_candidates.py`
  - Owns `ItKeywordCandidate`, KiWi-backed tokenization, deterministic candidate scoring, prompt candidate formatting, and LLM output filtering.
  - No DB access and no Ollama calls.
- Modify `ai/post_analysis/common/constant.py`
  - Adds IC02 candidate extraction constants, prompt labels, stopwords, allowed POS tags, and scoring values.
- Modify `ai/post_analysis/analyze_it_keywords.py`
  - Builds candidate keywords from `title + compressed_content`.
  - Adds `[candidate_keywords]` to prompts.
  - Keeps expansion prompt candidate-limited.
  - Filters final LLM keywords before merge.
- Modify `ai/post_analysis/tests/unit/test_l0_it_keywords.py`
  - Adds pure candidate extraction and filtering tests.
- Modify `ai/post_analysis/tests/unit/test_l3_analyze_it_keywords_indirect.py`
  - Adds orchestration tests for candidate empty/invalid LLM output behavior.
- Modify `ai/post_analysis/requirements.txt`
  - Adds `kiwipiepy`.

## Task 1: Add Candidate Config Contracts

**Files:**
- Modify: `ai/post_analysis/common/constant.py`
- Modify: `ai/post_analysis/tests/unit/test_l0_it_keywords.py`
- Modify: `ai/post_analysis/requirements.txt`

- [ ] **Step 1: Write failing config tests**

Append assertions to `test_pa_l0_itkw_001_config_defaults` and `test_pa_l0_itkw_009_preprocessing_config_defaults`:

```python
assert AnalyzeItKeywordsConfig.CANDIDATE_PROMPT_LABEL == "[candidate_keywords]"
assert AnalyzeItKeywordsConfig.MAX_PROMPT_CANDIDATES == 40
assert AnalyzeItKeywordsConfig.MIN_CANDIDATE_SCORE > 0
assert "후보군" in AnalyzeItKeywordsConfig.PROMPT_CANDIDATE_LIMIT_GUIDE
assert "이해" in AnalyzeItKeywordsConfig.CANDIDATE_STOPWORDS
assert "NNG" in AnalyzeItKeywordsConfig.CANDIDATE_NOUN_POS_TAGS
assert "VA" in AnalyzeItKeywordsConfig.CANDIDATE_SIGNAL_POS_TAGS
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```powershell
C:\dev\Project\SK-Connect\.venv\Scripts\python.exe -m pytest ai\post_analysis\tests\unit\test_l0_it_keywords.py::test_pa_l0_itkw_001_config_defaults ai\post_analysis\tests\unit\test_l0_it_keywords.py::test_pa_l0_itkw_009_preprocessing_config_defaults -v
```

Expected: FAIL because new constants do not exist.

- [ ] **Step 3: Add config constants**

Add to `AnalyzeItKeywordsConfig`:

```python
CANDIDATE_PROMPT_LABEL = "[candidate_keywords]"
PROMPT_CANDIDATE_LIMIT_GUIDE = (
    "- keywords는 candidate_keywords에 있는 문자열만 사용합니다. 후보군 밖 새 키워드나 임의 합성어를 만들지 않습니다."
)
MAX_PROMPT_CANDIDATES = 40
MIN_CANDIDATE_SCORE = 2
CANDIDATE_MAX_KEYWORD_CHARS = 40
CANDIDATE_MIN_KEYWORD_CHARS = 2
CANDIDATE_TITLE_WEIGHT = 5
CANDIDATE_EARLY_CONTENT_WEIGHT = 3
CANDIDATE_FREQUENCY_WEIGHT = 2
CANDIDATE_TECH_PATTERN_WEIGHT = 3
CANDIDATE_IMPORTANT_TERM_WEIGHT = 2
CANDIDATE_SIGNAL_NEARBY_WEIGHT = 2
CANDIDATE_NOUN_POS_TAGS = ("NNG", "NNP", "SL", "SN")
CANDIDATE_SIGNAL_POS_TAGS = ("VV", "VA", "XR")
CANDIDATE_STOPWORDS = (
    "이해",
    "필요",
    "가능",
    "사용",
    "지원",
    "기반",
    "관련",
    "내용",
    "부분",
)
CANDIDATE_SIGNAL_TERMS = (
    "개선",
    "지원",
    "공개",
    "변경",
    "삭제",
    "검증",
    "자동화",
    "최적화",
    "절감",
    "통합",
    "배포",
    "확장",
)
```

Add to `requirements.txt`:

```text
kiwipiepy
```

- [ ] **Step 4: Run config tests**

Run the same command from Step 2.

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add ai\post_analysis\common\constant.py ai\post_analysis\tests\unit\test_l0_it_keywords.py ai\post_analysis\requirements.txt
git commit -m "feat: add ic02 keyword candidate config"
```

## Task 2: Add KiWi Candidate Extraction Helpers

**Files:**
- Create: `ai/post_analysis/common/it_keyword_candidates.py`
- Modify: `ai/post_analysis/tests/unit/test_l0_it_keywords.py`

- [ ] **Step 1: Write failing pure helper tests**

Add imports:

```python
from common.it_keyword_candidates import (
    extract_it_keyword_candidates,
    filter_it_keywords_by_candidates,
    format_candidate_keywords_for_prompt,
)
```

Add tests:

```python
def test_pa_l0_itkw_021_candidate_extraction_keeps_source_terms() -> None:
    candidates = extract_it_keyword_candidates(
        "git-sync 리모트 미러링",
        "로컬 체크아웃 없이 소스 리모트에서 타겟 리모트로 ref와 오브젝트를 직접 스트리밍합니다. 메모리 사용량은 일정합니다.",
    )
    texts = [candidate.text for candidate in candidates]
    assert "git-sync" in texts
    assert "소스 리모트" in texts
    assert "타겟 리모트" in texts
    assert "메모리 사용량" in texts


def test_pa_l0_itkw_022_candidate_filter_rejects_generated_composites() -> None:
    candidates = extract_it_keyword_candidates(
        "git-sync 리모트 미러링",
        "소스 리모트에서 타겟 리모트로 ref와 오브젝트를 직접 스트리밍하며 메모리 사용량은 일정합니다.",
    )
    filtered = filter_it_keywords_by_candidates(
        [
            "git-sync",
            "타겟 리모트",
            "Git 레미트리치닝",
            "타겟 리먼트 관리",
            "프로덕션 배포",
        ],
        candidates,
    )
    assert filtered == ["git-sync", "타겟 리모트"]


def test_pa_l0_itkw_023_candidate_filter_rejects_low_quality_words() -> None:
    candidates = extract_it_keyword_candidates(
        "ZFS 튜닝",
        "무작위 접근 워크로드에서는 recordsize와 ARC 메모리 캐시, IO 병합을 함께 검토합니다.",
    )
    filtered = filter_it_keywords_by_candidates(
        ["ZFS", "recordsize", "박스크립트 시스템", "이해 필요", "ARC 메모리 캐시"],
        candidates,
    )
    assert filtered == ["ZFS", "recordsize", "ARC 메모리 캐시"]


def test_pa_l0_itkw_024_candidate_prompt_format_is_ranked_and_limited() -> None:
    candidates = extract_it_keyword_candidates(
        "NVIDIA Agent Skills",
        "NVIDIA Agent Skills는 CUDA-X 라이브러리와 SkillSpector 검증 파이프라인을 제공합니다.",
    )
    prompt_text = format_candidate_keywords_for_prompt(candidates, limit=3)
    assert prompt_text.count("\n") <= 2
    assert "NVIDIA Agent Skills" in prompt_text
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```powershell
C:\dev\Project\SK-Connect\.venv\Scripts\python.exe -m pytest ai\post_analysis\tests\unit\test_l0_it_keywords.py::test_pa_l0_itkw_021_candidate_extraction_keeps_source_terms ai\post_analysis\tests\unit\test_l0_it_keywords.py::test_pa_l0_itkw_022_candidate_filter_rejects_generated_composites ai\post_analysis\tests\unit\test_l0_it_keywords.py::test_pa_l0_itkw_023_candidate_filter_rejects_low_quality_words ai\post_analysis\tests\unit\test_l0_it_keywords.py::test_pa_l0_itkw_024_candidate_prompt_format_is_ranked_and_limited -v
```

Expected: FAIL because `common.it_keyword_candidates` does not exist.

- [ ] **Step 3: Implement candidate module**

Create `common/it_keyword_candidates.py` with:

```python
"""IC02 IT 키워드 후보군 추출과 LLM 결과 검증."""

from __future__ import annotations

from dataclasses import dataclass
import re

from kiwipiepy import Kiwi

from common.constant import AnalyzeItKeywordsConfig


@dataclass(frozen=True)
class ItKeywordCandidate:
    """원문 기반 IC02 키워드 후보."""

    text: str
    score: int
    source: str
    frequency: int


_KIWI: Kiwi | None = None


def _get_kiwi() -> Kiwi:
    global _KIWI
    if _KIWI is None:
        _KIWI = Kiwi()
    return _KIWI
```

Implement helpers:

- `_normalize_candidate_text(text: str) -> str`
- `_contains_tech_pattern(text: str) -> bool`
- `_is_stopword(text: str) -> bool`
- `_source_for_candidate(text, title, content) -> str`
- `_score_candidate(text, frequency, source, title, content) -> int`
- `extract_it_keyword_candidates(title, content) -> list[ItKeywordCandidate]`
- `format_candidate_keywords_for_prompt(candidates, limit=AnalyzeItKeywordsConfig.MAX_PROMPT_CANDIDATES) -> str`
- `filter_it_keywords_by_candidates(keywords, candidates) -> list[str]`

Implementation rules:

- Use KiWi token POS tags from config.
- Build candidates from contiguous noun/SL/SN token runs.
- Keep source surface text only.
- Add regex fallback for hyphenated English names like `git-sync`.
- Drop stopwords, one-character values, numeric-only values, overlong values.
- Sort by `score desc`, `frequency desc`, `text`.
- Filter LLM keywords by exact normalized candidate text only.

- [ ] **Step 4: Run pure helper tests**

Run the same command from Step 2.

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add ai\post_analysis\common\it_keyword_candidates.py ai\post_analysis\tests\unit\test_l0_it_keywords.py
git commit -m "feat: add ic02 keyword candidate extraction"
```

## Task 3: Wire Candidates Into Prompt And Result Filtering

**Files:**
- Modify: `ai/post_analysis/analyze_it_keywords.py`
- Modify: `ai/post_analysis/tests/unit/test_l0_it_keywords.py`
- Modify: `ai/post_analysis/tests/unit/test_l3_analyze_it_keywords_indirect.py`

- [ ] **Step 1: Write failing prompt and extraction tests**

Add L0 tests:

```python
def test_pa_l0_itkw_025_prompt_includes_candidate_keywords() -> None:
    prompt = build_it_keyword_prompt(
        {
            "title": "NVIDIA Agent Skills",
            "content": "NVIDIA Agent Skills는 CUDA-X 라이브러리와 SkillSpector 검증 파이프라인을 제공합니다.",
        }
    )
    assert AnalyzeItKeywordsConfig.CANDIDATE_PROMPT_LABEL in prompt
    assert "후보군 밖 새 키워드" in prompt
    assert "NVIDIA Agent Skills" in prompt


@patch("analyze_it_keywords._ollama_chat_json")
def test_pa_l0_itkw_026_extract_filters_llm_keywords_by_candidates(mock_chat: MagicMock) -> None:
    mock_chat.return_value = {
        "summary": "git-sync 요약",
        "flow": "동기화 -> 메모리 영향",
        "interest_label": "medium",
        "keywords": ["git-sync", "타겟 리모트", "Git 레미트리치닝", "프로덕션 배포"],
    }
    result = extract_it_keywords(
        {
            "title": "git-sync 리모트 미러링",
            "content": "소스 리모트에서 타겟 리모트로 ref와 오브젝트를 직접 스트리밍하며 메모리 사용량은 일정합니다.",
        }
    )
    assert result.keywords == ["git-sync", "타겟 리모트"]
```

Add L3 test:

```python
@patch("analyze_it_keywords.merge_analysis_data")
@patch("analyze_it_keywords._ollama_chat_json")
@patch("analyze_it_keywords.get_crawling_data")
@patch("analyze_it_keywords.get_analysis_data")
def test_pa_l3_itkw_010_invalid_candidate_keywords_skip_merge(
    mock_get_analysis: MagicMock,
    mock_get_crawling: MagicMock,
    mock_chat: MagicMock,
    mock_merge: MagicMock,
) -> None:
    mock_get_analysis.return_value = pd.DataFrame(
        {
            AnalysisColumn.CRAWLING_ID.value: [901],
            AnalysisColumn.TITLE.value: ["git-sync 리모트 미러링"],
            AnalysisColumn.CONTENT.value: ["소스 리모트에서 타겟 리모트로 ref와 오브젝트를 직접 스트리밍합니다."],
            AnalysisColumn.KEYWORDS.value: [pd.NA],
            AnalysisColumn.INFORMATION_CD.value: [CodeTable.INFORMATION_IT_INFO.value],
        }
    )
    mock_get_crawling.return_value = pd.DataFrame()
    mock_chat.return_value = {
        "summary": "요약",
        "flow": "흐름",
        "interest_label": "low",
        "keywords": ["Git 레미트리치닝", "프로덕션 배포"],
    }
    analyze_it_keywords()
    mock_merge.assert_not_called()
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```powershell
C:\dev\Project\SK-Connect\.venv\Scripts\python.exe -m pytest ai\post_analysis\tests\unit\test_l0_it_keywords.py::test_pa_l0_itkw_025_prompt_includes_candidate_keywords ai\post_analysis\tests\unit\test_l0_it_keywords.py::test_pa_l0_itkw_026_extract_filters_llm_keywords_by_candidates ai\post_analysis\tests\unit\test_l3_analyze_it_keywords_indirect.py::test_pa_l3_itkw_010_invalid_candidate_keywords_skip_merge -v
```

Expected: FAIL because prompt/result filtering is not wired.

- [ ] **Step 3: Wire implementation**

Modify `analyze_it_keywords.py`:

```python
from common.it_keyword_candidates import (
    extract_it_keyword_candidates,
    filter_it_keywords_by_candidates,
    format_candidate_keywords_for_prompt,
)
```

Add candidate helpers near prompt building:

```python
def _build_candidate_context(title: str, compressed_content: str) -> tuple[list, str]:
    candidates = extract_it_keyword_candidates(title, compressed_content)
    candidate_prompt = format_candidate_keywords_for_prompt(candidates)
    return candidates, candidate_prompt
```

Update `build_it_keyword_prompt`:

```python
candidates, candidate_prompt = _build_candidate_context(title, compressed_content)
if not candidates:
    raise ValueError("IC02 키워드 후보군이 비어 있습니다.")
...
AnalyzeItKeywordsConfig.PROMPT_CANDIDATE_LIMIT_GUIDE,
...
f"{AnalyzeItKeywordsConfig.CANDIDATE_PROMPT_LABEL}\n{candidate_prompt}",
```

Update `extract_it_keywords` so the same candidate list filters both first and expansion result:

```python
title = _text_or_empty(row.get(AnalysisColumn.TITLE.value))
compressed_content = preprocess_it_content(row)
candidates = extract_it_keyword_candidates(title, compressed_content)
if not candidates:
    raise ValueError("IC02 키워드 후보군이 비어 있습니다.")
prompt = build_it_keyword_prompt(row, compressed_content=compressed_content, candidates=candidates)
result = ItKeywordResult(**_ollama_chat_json(prompt))
result.keywords = filter_it_keywords_by_candidates(result.keywords, candidates)
...
expanded_result.keywords = filter_it_keywords_by_candidates(expanded_result.keywords, candidates)
```

Allow optional parameters on `build_it_keyword_prompt` to avoid recomputing:

```python
def build_it_keyword_prompt(
    row: dict | pd.Series,
    *,
    compressed_content: str | None = None,
    candidates: list | None = None,
) -> str:
```

- [ ] **Step 4: Run targeted tests**

Run the same command from Step 2.

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add ai\post_analysis\analyze_it_keywords.py ai\post_analysis\tests\unit\test_l0_it_keywords.py ai\post_analysis\tests\unit\test_l3_analyze_it_keywords_indirect.py
git commit -m "feat: constrain ic02 keywords to source candidates"
```

## Task 4: Focused Verification And Selected Keyword Check

**Files:**
- No code changes unless verification exposes a defect.

- [ ] **Step 1: Run IC02 focused tests**

```powershell
C:\dev\Project\SK-Connect\.venv\Scripts\python.exe -m pytest ai\post_analysis\tests\unit\test_l0_it_keywords.py ai\post_analysis\tests\unit\test_l3_analyze_it_keywords_indirect.py ai\post_analysis\tests\unit\test_l3_run_pipeline_indirect.py -v
```

Expected: PASS.

- [ ] **Step 2: Run full post_analysis tests**

```powershell
C:\dev\Project\SK-Connect\.venv\Scripts\python.exe -m pytest ai\post_analysis\tests -v
```

Expected: PASS.

- [ ] **Step 3: Inspect selected candidates for known bad examples**

Run:

```powershell
cd C:\dev\Project\SK-Connect\ai\post_analysis
C:\dev\Project\SK-Connect\.venv\Scripts\python.exe -c "from common.it_keyword_candidates import extract_it_keyword_candidates, filter_it_keywords_by_candidates; title='git-sync - 로컬 체크아웃 없이 Git 리모트 간 ref를 직접 미러링하는 CLI 도구'; content='로컬 클론 필요없이 소스 리모트에서 타겟 리모트로 ref와 오브젝트를 직접 스트리밍하며 메모리 사용량은 일정함'; candidates=extract_it_keyword_candidates(title, content); print([c.text for c in candidates[:20]]); print(filter_it_keywords_by_candidates(['git-sync','타겟 리모트','Git 레미트리치닝','프로덕션 배포'], candidates))"
```

Expected:

```text
Git 레미트리치닝 is absent from candidates and filtered output.
프로덕션 배포 is filtered out unless it appears in the source text.
```

- [ ] **Step 4: Report selected-part check**

Report:

- Top candidate examples.
- Which LLM-provided values would be accepted.
- Which values would be rejected.
- Whether ID 4/5 bad keyword classes are blocked.

- [ ] **Step 5: Commit verification fixes only if needed**

If verification requires changes, first run:

```powershell
git status --short
```

Then stage only the files shown as changed by the verification fix. Expected fix files are limited to:

```powershell
git add ai\post_analysis\analyze_it_keywords.py ai\post_analysis\common\it_keyword_candidates.py ai\post_analysis\common\constant.py ai\post_analysis\tests\unit\test_l0_it_keywords.py ai\post_analysis\tests\unit\test_l3_analyze_it_keywords_indirect.py
git commit -m "fix: harden ic02 candidate validation"
```

If no files changed, do not create an empty commit.

## Self-Review Checklist

- [ ] Every changed behavior has a failing test first.
- [ ] Candidate extraction is DB-free and Ollama-free.
- [ ] LLM is constrained by `candidate_keywords`.
- [ ] Saved keywords are filtered by candidates.
- [ ] IC01 modules are untouched.
- [ ] Full `ai/post_analysis` tests pass.
