"""PA-L2-ITKW-BENCH: IC02 회사 매칭 벤치마크 helper."""

from __future__ import annotations

import pandas as pd

from benchmark_it_keywords import build_it_keyword_benchmark_report
from common.constant import AnalysisColumn


def test_pa_l2_itkw_bench_001_counts_company_matched_and_unmatched_rows() -> None:
    """벤치마크 리포트는 LLM selector가 아니라 회사 매칭 여부를 집계한다."""
    rows = pd.DataFrame(
        {
            AnalysisColumn.CRAWLING_ID.value: [1, 2],
            AnalysisColumn.TITLE.value: ["OpenAI release", "Open source release"],
            AnalysisColumn.CONTENT.value: ["ChatGPT 개발사 업데이트", "회사명 없음"],
        }
    )

    report = build_it_keyword_benchmark_report(rows)

    assert report["sample_size"] == 2
    assert report["company_matched_count"] == 1
    assert report["company_unmatched_count"] == 1
    assert report["rows"][0]["matched_companies"] == ["OpenAI"]
    assert report["rows"][0]["company_types"] == ["ai_company"]
    assert report["rows"][1]["matched_companies"] == []
    assert "llm_selector" not in report
