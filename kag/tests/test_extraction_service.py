import json
from pathlib import Path

from kag_graph.extraction.dictionary_resolver import DictionaryEntry, DictionaryResolver
from kag_graph.extraction.extraction_service import ExtractionService
from kag_graph.extraction.models import ReviewReason
from kag_graph.extraction.providers.mock_llm_client import MockLLMKeywordClassifier
from kag_graph.extraction.writer.keyword_extraction_writer import KeywordExtractionWriter


def test_extraction_service_writes_partial_success_review_and_malformed_outputs(tmp_path: Path):
    input_file = tmp_path / "normalized_article_batch-1.jsonl"
    records = [
        {
            "schema_version": "news.article.v1",
            "article_id": "a1",
            "source": "geeknews",
            "category_cd": "IC02",
            "title": "OpenAI GPT 출시",
            "content": "OpenAI가 GPT 서비스를 출시했다.",
            "batch_id": "batch-1",
            "run_attempt": 1,
        },
        {
            "schema_version": "news.article.v1",
            "article_id": "bad",
            "source": "geeknews",
            "category_cd": "IC02",
            "title": "",
            "content": "본문",
            "batch_id": "batch-1",
            "run_attempt": 1,
        },
    ]
    input_file.write_text("\n".join(json.dumps(record, ensure_ascii=False) for record in records), encoding="utf-8")
    writer = KeywordExtractionWriter(base_dir=tmp_path / "out", clock=lambda: "20260513T213012")
    service = ExtractionService(
        dictionary_resolver=DictionaryResolver([DictionaryEntry("OpenAI", "Company", ("openai",))]),
        llm_classifier=MockLLMKeywordClassifier(should_fail=True),
        writer=writer,
        created_at_factory=lambda: "2026-05-13T21:30:12+09:00",
    )

    result = service.extract(input_file)

    success_rows = [
        json.loads(line)
        for line in result.success_file.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    fail_rows = [
        json.loads(line)
        for line in result.malformed_file.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    metrics = json.loads(result.metrics_file.read_text(encoding="utf-8"))

    assert len(success_rows) == 1
    assert success_rows[0]["article_id"] == "a1"
    assert success_rows[0]["keywords"][0]["canonical_name"] == "OpenAI"
    assert success_rows[0]["event_signals"][0]["matched_text"] == "출시"
    assert success_rows[0]["review_required"] is True
    assert ReviewReason.LLM_CLASSIFICATION_FAILED in success_rows[0]["review_reasons"]
    assert len(fail_rows) == 1
    assert fail_rows[0]["reason_code"] == "EMPTY_TITLE"
    assert metrics["status"] == "PARTIAL_SUCCESS"
    assert metrics["success_article_count"] == 1
    assert metrics["malformed_article_count"] == 1
