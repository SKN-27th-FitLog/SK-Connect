# IC02 Deterministic Quality Gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Increase IC02 deterministic keyword coverage without storing low-quality deterministic candidates.

**Architecture:** Keep candidate extraction and LLM selector behavior unchanged. Add stricter quality checks only to the deterministic skip path, then lower the deterministic average-score threshold from 17 to 16.

**Tech Stack:** Python, pandas, pytest, existing IC02 KiWi candidate extraction helpers.

---

### Task 1: Add Deterministic Quality Guard Tests

**Files:**
- Modify: `ai/post_analysis/tests/unit/test_l0_it_keywords.py`

- [ ] **Step 1: Write failing tests**

Add tests proving malformed deterministic candidates are rejected and clean score-16 candidates can pass.

- [ ] **Step 2: Verify RED**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest ai\post_analysis\tests\unit\test_l0_it_keywords.py::test_pa_l0_itkw_036_candidate_confidence_rejects_low_quality_deterministic_candidates ai\post_analysis\tests\unit\test_l0_it_keywords.py::test_pa_l0_itkw_037_candidate_confidence_accepts_quality_candidates_at_score_16 -v
```

Expected: FAIL before implementation.

### Task 2: Implement Quality Gate

**Files:**
- Modify: `ai/post_analysis/common/constant.py`
- Modify: `ai/post_analysis/analyze_it_keywords.py`

- [ ] **Step 1: Add deterministic quality constants**

Set `DETERMINISTIC_MIN_AVERAGE_SCORE = 16` and add focused blocked token/signal constants if needed.

- [ ] **Step 2: Reject low-quality deterministic candidates**

Update `_is_deterministic_candidate` so LLM fallback still receives candidates, but deterministic skip refuses broken fragments and weak sentence pieces.

- [ ] **Step 3: Verify GREEN**

Run the RED command again and confirm PASS.

### Task 3: Benchmark And Regression

**Files:**
- Generated: `test-results/it-keyword-benchmark/...`
- Generated: `test-results/e2e-report/...`
- Generated: `test-results/e2e-screenshots/...`

- [ ] **Step 1: Run focused and full tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest ai\post_analysis\tests\unit\test_l0_it_keywords.py ai\post_analysis\tests\unit\test_l3_analyze_it_keywords_indirect.py -v
.\.venv\Scripts\python.exe -m pytest ai\post_analysis -v
```

- [ ] **Step 2: Run benchmark**

Run:

```powershell
.\.venv\Scripts\python.exe ai\post_analysis\benchmark_it_keywords.py --max-rows 50 --output-dir test-results\it-keyword-benchmark\current-50-after-deterministic-quality-gate
```

- [ ] **Step 3: Capture image report**

Generate an HTML summary and Playwright screenshots under `test-results/e2e-screenshots`.
