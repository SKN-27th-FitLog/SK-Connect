"""PA-L2-ITKW-BENCH: IC02 keyword strategy benchmark helpers."""

from __future__ import annotations

import pandas as pd

from benchmark_it_keywords import build_it_keyword_benchmark_report
from common.constant import AnalysisColumn
from common.it_keyword_candidates import ItKeywordCandidate


def test_pa_l2_itkw_bench_001_counts_deterministic_and_llm_fallback_rows(
    monkeypatch,
) -> None:
    rows = pd.DataFrame(
        {
            AnalysisColumn.CRAWLING_ID.value: [1, 2],
            AnalysisColumn.TITLE.value: ["strong", "weak"],
            AnalysisColumn.CONTENT.value: ["strong content", "weak content"],
        }
    )

    def fake_candidates(title: object, content: object) -> list[ItKeywordCandidate]:
        if str(title) == "strong":
            return [
                ItKeywordCandidate(f"strong-{index:02d}", 24 - index, "both", 2)
                for index in range(1, 16)
            ]
        return [
            ItKeywordCandidate(f"weak-{index:02d}", 10, "content", 1)
            for index in range(1, 16)
        ]

    monkeypatch.setattr("benchmark_it_keywords.preprocess_it_content", lambda row: row["content"])
    monkeypatch.setattr("benchmark_it_keywords.extract_it_keyword_candidates", fake_candidates)

    report = build_it_keyword_benchmark_report(rows, measured_llm_seconds=200.0)

    assert report["sample_size"] == 2
    assert report["strategy_counts"] == {
        "deterministic": 1,
        "llm_selector": 1,
    }
    assert report["estimated_saved_llm_calls"] == 1
    assert report["estimated_saved_seconds"] == 200.0
    assert report["rows"][0]["strategy"] == "deterministic"
    assert report["rows"][1]["strategy"] == "llm_selector"
