"""IC02 회사 매칭 상태를 DB 변경 없이 확인하는 helper."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

import common.env  # noqa: F401 - local DB 환경변수 로드
from common.constant import AnalysisColumn, AnalyzeItKeywordsConfig
from common.it_company_registry import (
    build_company_keyword_values,
    match_it_companies,
)
from postgresql.run_query import get_it_keyword_target_data


def _row_value(row: pd.Series, column: str, default: object = "") -> object:
    return row[column] if column in row else default


def _keyword_string(values: list[str]) -> str:
    return "".join(f"#{value}" for value in values if value)


def build_it_keyword_benchmark_report(df: pd.DataFrame) -> dict[str, Any]:
    """샘플 DataFrame의 IC02 회사 매칭 상태 리포트를 만든다."""
    rows: list[dict[str, Any]] = []
    company_matched_count = 0

    for _, row in df.iterrows():
        companies = match_it_companies(
            title=_row_value(row, AnalysisColumn.TITLE.value),
            content=_row_value(row, AnalysisColumn.CONTENT.value),
        )
        keyword_values = build_company_keyword_values(companies)
        if companies:
            company_matched_count += 1
        rows.append(
            {
                "crawling_id": _row_value(row, AnalysisColumn.CRAWLING_ID.value, None),
                "title": _row_value(row, AnalysisColumn.TITLE.value),
                "matched_companies": [company.canonical_name for company in companies],
                "company_types": [company.company_type for company in companies],
                "keywords": _keyword_string(keyword_values),
            }
        )

    sample_size = int(len(df))
    return {
        "sample_size": sample_size,
        "company_matched_count": company_matched_count,
        "company_unmatched_count": sample_size - company_matched_count,
        "rows": rows,
    }


def write_it_keyword_benchmark_report(
    report: dict[str, Any],
    output_dir: Path,
) -> tuple[Path, Path]:
    """JSON과 Markdown 리포트를 쓴다."""
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "it-company-keyword-benchmark.json"
    md_path = output_dir / "it-company-keyword-benchmark.md"
    json_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )

    lines = [
        "# IT Company Keyword Benchmark",
        "",
        f"- sample_size: {report['sample_size']}",
        f"- company_matched_count: {report['company_matched_count']}",
        f"- company_unmatched_count: {report['company_unmatched_count']}",
        "",
        "| crawling_id | matched_companies | company_types | title |",
        "|---:|---|---|---|",
    ]
    for row in report["rows"]:
        title = str(row["title"]).replace("|", "\\|")
        companies = ", ".join(row["matched_companies"])
        company_types = ", ".join(row["company_types"])
        lines.append(f"| {row['crawling_id']} | {companies} | {company_types} | {title} |")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, md_path


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Benchmark IC02 company keyword matching.")
    parser.add_argument(
        "--max-rows",
        type=int,
        default=AnalyzeItKeywordsConfig.BENCHMARK_DEFAULT_SAMPLE_ROWS,
    )
    parser.add_argument("--output-dir", type=Path, default=None)
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    df = get_it_keyword_target_data(max_rows=args.max_rows)
    report = build_it_keyword_benchmark_report(df)
    output_dir = args.output_dir or (
        Path("test-results")
        / "it-company-keyword-benchmark"
        / datetime.now().strftime("%Y%m%d-%H%M%S")
    )
    json_path, md_path = write_it_keyword_benchmark_report(report, output_dir)
    print(f"JSON={json_path}")
    print(f"MARKDOWN={md_path}")


if __name__ == "__main__":
    main()
