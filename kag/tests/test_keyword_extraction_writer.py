import json
from pathlib import Path

from kag_graph.extraction.models import ClassifiedKeyword, EventSignal, NormalizedArticle, ReviewReason
from kag_graph.extraction.writer.keyword_extraction_writer import KeywordExtractionWriter


def test_writer_creates_non_overwrite_success_fail_and_metrics_files(tmp_path: Path):
    writer = KeywordExtractionWriter(base_dir=tmp_path, clock=lambda: "20260513T213012")
    article = NormalizedArticle.from_dict(
        {
            "schema_version": "news.article.v1",
            "article_id": "a1",
            "source": "geeknews",
            "category_cd": "IC02",
            "title": "OpenAI 출시",
            "content": "ChatGPT 출시",
            "batch_id": "batch-1",
            "run_attempt": 1,
        }
    )
    record = article.to_extraction_record(
        keywords=[ClassifiedKeyword("OpenAI", "OpenAI", "Company", 0.9, 1.0, "dictionary")],
        event_signals=[EventSignal("RELEASE", "출시", 0.8, "morph_action_dictionary")],
        review_required=True,
        review_reasons=[ReviewReason.LOW_KEYWORD_COUNT],
        created_at="2026-05-13T21:30:12+09:00",
    )

    success_file = writer.write_success("batch-1", [record])
    fail_file = writer.write_malformed("batch-1", [])
    metrics_file = writer.write_metrics("batch-1", record_count=1, malformed_count=0, review_required_count=1, keyword_count=1)

    assert success_file == tmp_path / "keyword_extraction_batch-1_20260513T213012.jsonl"
    assert fail_file == tmp_path / "status=fail/malformed_article_batch-1_20260513T213012.jsonl"
    assert metrics_file == tmp_path / "status=metrics/keyword_extraction_metrics_batch-1_20260513T213012.json"
    assert json.loads(success_file.read_text(encoding="utf-8").splitlines()[0])["article_id"] == "a1"
    assert json.loads(metrics_file.read_text(encoding="utf-8"))["status"] == "SUCCESS"


def test_writer_does_not_overwrite_when_timestamp_collides(tmp_path: Path):
    writer = KeywordExtractionWriter(base_dir=tmp_path, clock=lambda: "20260513T213012")

    first_file = writer.write_success("batch-1", [])
    second_file = writer.write_success("batch-1", [])

    assert first_file.name == "keyword_extraction_batch-1_20260513T213012.jsonl"
    assert second_file.name == "keyword_extraction_batch-1_20260513T213012_2.jsonl"
    assert first_file.exists()
    assert second_file.exists()
