"""Benchmark IC02 keyword extraction strategy without mutating DB rows."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

import common.env  # noqa: F401 - load local environment
from analyze_it_keywords import (
    evaluate_it_keyword_candidate_confidence,
    preprocess_it_content,
)
from common.constant import AnalysisColumn, AnalyzeItKeywordsConfig
from common.it_keyword_candidates import extract_it_keyword_candidates
from postgresql.run_query import get_it_keyword_target_data


def _row_value(row: pd.Series, column: str, default: object = "") -> object:
    return row[column] if column in row else default


def build_it_keyword_benchmark_report(
    df: pd.DataFrame,
    *,
    measured_llm_seconds: float = AnalyzeItKeywordsConfig.BENCHMARK_DEFAULT_MEASURED_LLM_SECONDS,
) -> dict[str, Any]:
    """Build a deterministic-first strategy report for a sample DataFrame."""
    rows: list[dict[str, Any]] = []
    strategy_counts = {"deterministic": 0, "llm_selector": 0}

    for _, row in df.iterrows():
        compressed_content = preprocess_it_content(row)
        candidates = extract_it_keyword_candidates(
            _row_value(row, AnalysisColumn.TITLE.value),
            compressed_content,
        )
        confidence = evaluate_it_keyword_candidate_confidence(candidates)
        strategy = "deterministic" if confidence.is_confident else "llm_selector"
        strategy_counts[strategy] += 1
        rows.append(
            {
                "crawling_id": _row_value(row, AnalysisColumn.CRAWLING_ID.value, None),
                "title": _row_value(row, AnalysisColumn.TITLE.value),
                "strategy": strategy,
                "candidate_count": confidence.candidate_count,
                "average_score": round(confidence.average_score, 3),
                "title_or_both_count": confidence.title_or_both_count,
                "repeated_or_title_count": confidence.repeated_or_title_count,
                "selected_keywords": confidence.keywords,
            }
        )

    saved_calls = strategy_counts["deterministic"]
    return {
        "sample_size": int(len(df)),
        "measured_llm_seconds": float(measured_llm_seconds),
        "strategy_counts": strategy_counts,
        "estimated_saved_llm_calls": saved_calls,
        "estimated_saved_seconds": round(saved_calls * measured_llm_seconds, 3),
        "rows": rows,
    }


def write_it_keyword_benchmark_report(
    report: dict[str, Any],
    output_dir: Path,
) -> tuple[Path, Path]:
    """Write JSON and Markdown benchmark reports."""
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "it-keyword-benchmark.json"
    md_path = output_dir / "it-keyword-benchmark.md"
    json_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )

    lines = [
        "# IT Keyword Strategy Benchmark",
        "",
        f"- sample_size: {report['sample_size']}",
        f"- measured_llm_seconds: {report['measured_llm_seconds']}",
        f"- deterministic: {report['strategy_counts']['deterministic']}",
        f"- llm_selector: {report['strategy_counts']['llm_selector']}",
        f"- estimated_saved_llm_calls: {report['estimated_saved_llm_calls']}",
        f"- estimated_saved_seconds: {report['estimated_saved_seconds']}",
        "",
        "| crawling_id | strategy | candidates | avg_score | title_or_both | title_or_repeated | title |",
        "|---:|---|---:|---:|---:|---:|---|",
    ]
    for row in report["rows"]:
        title = str(row["title"]).replace("|", "\\|")
        lines.append(
            "| "
            f"{row['crawling_id']} | {row['strategy']} | {row['candidate_count']} | "
            f"{row['average_score']} | {row['title_or_both_count']} | "
            f"{row['repeated_or_title_count']} | {title} |"
        )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, md_path


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Benchmark IC02 keyword strategy.")
    parser.add_argument(
        "--max-rows",
        type=int,
        default=AnalyzeItKeywordsConfig.BENCHMARK_DEFAULT_SAMPLE_ROWS,
    )
    parser.add_argument(
        "--measured-llm-seconds",
        type=float,
        default=AnalyzeItKeywordsConfig.BENCHMARK_DEFAULT_MEASURED_LLM_SECONDS,
    )
    parser.add_argument("--output-dir", type=Path, default=None)
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    df = get_it_keyword_target_data(max_rows=args.max_rows)
    report = build_it_keyword_benchmark_report(
        df,
        measured_llm_seconds=args.measured_llm_seconds,
    )
    output_dir = args.output_dir or (
        Path("test-results")
        / "it-keyword-benchmark"
        / datetime.now().strftime("%Y%m%d-%H%M%S")
    )
    json_path, md_path = write_it_keyword_benchmark_report(report, output_dir)
    print(f"JSON={json_path}")
    print(f"MARKDOWN={md_path}")
    print(json.dumps(report, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
