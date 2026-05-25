from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from kag_graph.extraction.corpus_context_builder import CorpusContextBuilder
from kag_graph.extraction.dictionary_resolver import DictionaryResolver
from kag_graph.extraction.hybrid_keyword_ranker import HybridKeywordRanker
from kag_graph.extraction.keyword_schema_validator import KeywordSchemaValidator
from kag_graph.extraction.models import KeywordExtractionRecord, MalformedArticleRecord, MalformedReason, NormalizedArticle
from kag_graph.extraction.preprocessing.action_signal_extractor import ActionSignalExtractor
from kag_graph.extraction.preprocessing.candidate_phrase_builder import CandidatePhraseBuilder
from kag_graph.extraction.preprocessing.korean_morph_analyzer import KoreanMorphAnalyzer
from kag_graph.extraction.preprocessing.token_filter import TokenFilter
from kag_graph.extraction.providers.mock_llm_client import MockLLMKeywordClassifier
from kag_graph.extraction.writer.keyword_extraction_writer import KeywordExtractionWriter


@dataclass(frozen=True)
class ExtractionServiceResult:
    success_file: Path
    malformed_file: Path
    metrics_file: Path


class ExtractionService:
    def __init__(
        self,
        dictionary_resolver: DictionaryResolver | None = None,
        llm_classifier: MockLLMKeywordClassifier | None = None,
        writer: KeywordExtractionWriter | None = None,
        created_at_factory: Callable[[], str] | None = None,
    ):
        self._morph_analyzer = KoreanMorphAnalyzer()
        self._token_filter = TokenFilter()
        self._candidate_builder = CandidatePhraseBuilder()
        self._action_signal_extractor = ActionSignalExtractor()
        self._corpus_builder = CorpusContextBuilder()
        self._ranker = HybridKeywordRanker()
        self._dictionary_resolver = dictionary_resolver or DictionaryResolver()
        self._llm_classifier = llm_classifier or MockLLMKeywordClassifier()
        self._validator = KeywordSchemaValidator()
        self._writer = writer or KeywordExtractionWriter(Path("."))
        self._created_at_factory = created_at_factory or (lambda: datetime.now().astimezone().isoformat())

    def extract(self, input_file: Path) -> ExtractionServiceResult:
        raw_rows = self._read_jsonl(input_file)
        articles: list[NormalizedArticle] = []
        malformed: list[MalformedArticleRecord] = []

        for row in raw_rows:
            try:
                articles.append(NormalizedArticle.from_dict(row))
            except ValueError as exc:
                malformed.append(self._malformed_from_row(row, str(exc)))

        batch_id = self._batch_id(articles, raw_rows)
        corpus_context = self._corpus_builder.build(articles)
        success_records = [self._extract_article(article, corpus_context) for article in articles]

        success_file = self._writer.write_success(batch_id, success_records)
        malformed_file = self._writer.write_malformed(batch_id, malformed)
        metrics_file = self._writer.write_metrics(
            batch_id=batch_id,
            record_count=len(success_records),
            malformed_count=len(malformed),
            review_required_count=sum(1 for record in success_records if record.review_required),
            keyword_count=sum(record.keyword_count for record in success_records),
        )
        return ExtractionServiceResult(success_file=success_file, malformed_file=malformed_file, metrics_file=metrics_file)

    def _extract_article(self, article: NormalizedArticle, corpus_context) -> KeywordExtractionRecord:
        tokens = self._token_filter.filter(self._morph_analyzer.analyze(article.document_text))
        candidates = self._candidate_builder.build(article.article_id, tokens, article.title, article.content)
        ranking_result = self._ranker.rank(article.article_id, candidates, corpus_context)
        dictionary_result = self._dictionary_resolver.resolve(ranking_result.keywords)
        llm_result = self._llm_classifier.classify_with_fallback(
            article_id=article.article_id,
            unresolved_candidates=dictionary_result.unresolved,
            dictionary_keywords=dictionary_result.resolved,
            title=article.title,
            content=article.content,
        )
        validation_result = self._validator.validate(
            article_id=article.article_id,
            keywords=llm_result.keywords,
            document_count=corpus_context.document_count,
            prior_review_reasons=[
                *ranking_result.review_reasons,
                *dictionary_result.review_reasons,
                *llm_result.review_reasons,
            ],
        )
        return article.to_extraction_record(
            keywords=validation_result.keywords,
            event_signals=self._action_signal_extractor.extract(article.document_text),
            review_required=validation_result.review_required,
            review_reasons=validation_result.review_reasons,
            created_at=self._created_at_factory(),
        )

    def _read_jsonl(self, input_file: Path) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        with input_file.open("r", encoding="utf-8") as file:
            for line in file:
                if not line.strip():
                    continue
                rows.append(json.loads(line))
        return rows

    def _malformed_from_row(self, row: dict[str, Any], reason_code: str) -> MalformedArticleRecord:
        return MalformedArticleRecord(
            article_id=_optional_text(row.get("article_id")),
            batch_id=_optional_text(row.get("batch_id")),
            run_attempt=_optional_int(row.get("run_attempt")),
            reason_code=reason_code or MalformedReason.ARTICLE_SCHEMA_INVALID,
            message=reason_code,
        )

    def _batch_id(self, articles: list[NormalizedArticle], raw_rows: list[dict[str, Any]]) -> str:
        if articles:
            return articles[0].batch_id
        for row in raw_rows:
            batch_id = _optional_text(row.get("batch_id"))
            if batch_id:
                return batch_id
        return "unknown_batch"


def _optional_text(value: Any) -> str | None:
    text = str(value).strip() if value is not None else ""
    return text or None


def _optional_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    return int(value)
