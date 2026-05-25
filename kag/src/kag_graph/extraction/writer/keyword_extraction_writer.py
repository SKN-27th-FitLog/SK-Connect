from __future__ import annotations

import json
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from kag_graph.extraction.models import ExtractionMetrics, KeywordExtractionRecord, MalformedArticleRecord


class KeywordExtractionWriter:
    def __init__(self, base_dir: Path, clock: Callable[[], str] | None = None):
        self._base_dir = base_dir
        self._clock = clock or (lambda: datetime.now().strftime("%Y%m%dT%H%M%S"))

    def write_success(self, batch_id: str, records: list[KeywordExtractionRecord]) -> Path:
        path = self._non_overwrite_path(self._base_dir / f"keyword_extraction_{batch_id}_{self._clock()}.jsonl")
        self._write_jsonl(path, [record.to_dict() for record in records])
        return path

    def write_malformed(self, batch_id: str, records: list[MalformedArticleRecord]) -> Path:
        path = self._non_overwrite_path(self._base_dir / "status=fail" / f"malformed_article_{batch_id}_{self._clock()}.jsonl")
        self._write_jsonl(path, [record.to_dict() for record in records])
        return path

    def write_metrics(
        self,
        batch_id: str,
        record_count: int,
        malformed_count: int,
        review_required_count: int,
        keyword_count: int,
    ) -> Path:
        metrics = ExtractionMetrics(
            total_article_count=record_count + malformed_count,
            success_article_count=record_count,
            malformed_article_count=malformed_count,
            review_required_count=review_required_count,
            total_keyword_count=keyword_count,
        )
        path = self._non_overwrite_path(self._base_dir / "status=metrics" / f"keyword_extraction_metrics_{batch_id}_{self._clock()}.json")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(metrics.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def _write_jsonl(self, path: Path, rows: list[dict]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        content = "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows)
        path.write_text(content, encoding="utf-8")

    def _non_overwrite_path(self, path: Path) -> Path:
        if not path.exists():
            return path

        counter = 2
        while True:
            candidate = path.with_name(f"{path.stem}_{counter}{path.suffix}")
            if not candidate.exists():
                return candidate
            counter += 1
