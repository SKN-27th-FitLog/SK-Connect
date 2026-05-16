from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


RANKING_METHOD = "tfidf_textrank_hybrid_v1"
KEYWORD_EXTRACTION_SCHEMA_VERSION = "news.keyword_extraction.v3"


class ReviewReason:
    LOW_KEYWORD_COUNT = "LOW_KEYWORD_COUNT"
    LOW_CONFIDENCE_KEYWORD = "LOW_CONFIDENCE_KEYWORD"
    SMALL_CORPUS_SIZE = "SMALL_CORPUS_SIZE"
    DICTIONARY_ALIAS_CONFLICT = "DICTIONARY_ALIAS_CONFLICT"
    LLM_CLASSIFICATION_FAILED = "LLM_CLASSIFICATION_FAILED"
    ALL_KEYWORDS_IGNORED = "ALL_KEYWORDS_IGNORED"


class MalformedReason:
    ARTICLE_SCHEMA_INVALID = "ARTICLE_SCHEMA_INVALID"
    EMPTY_TITLE = "EMPTY_TITLE"
    EMPTY_CONTENT = "EMPTY_CONTENT"
    KEYWORD_RANKING_FAILED = "KEYWORD_RANKING_FAILED"
    LLM_CLASSIFICATION_FAILED = "LLM_CLASSIFICATION_FAILED"
    LLM_RESPONSE_PARSE_FAILED = "LLM_RESPONSE_PARSE_FAILED"
    VALIDATOR_FAILED = "VALIDATOR_FAILED"
    ARTICLE_ID_MISMATCH = "ARTICLE_ID_MISMATCH"
    NO_VALID_KEYWORDS = "NO_VALID_KEYWORDS"
    UNKNOWN_EXTRACTION_ERROR = "UNKNOWN_EXTRACTION_ERROR"


class NodeType:
    TECHNOLOGY = "Technology"
    COMPANY = "Company"
    EVENT = "Event"
    TOPIC = "Topic"
    IGNORE = "Ignore"


ALLOWED_NODE_TYPES = {
    NodeType.TECHNOLOGY,
    NodeType.COMPANY,
    NodeType.EVENT,
    NodeType.TOPIC,
    NodeType.IGNORE,
}


@dataclass(frozen=True)
class NormalizedArticle:
    schema_version: str
    article_id: str
    source: str
    category_cd: str
    title: str
    content: str
    url: str
    content_hash: str
    batch_id: str
    run_attempt: int
    published_at: str | None = None

    @classmethod
    def from_dict(cls, record: dict[str, Any]) -> "NormalizedArticle":
        required_fields = ("schema_version", "article_id", "source", "category_cd", "batch_id", "run_attempt")
        for field_name in required_fields:
            if record.get(field_name) in (None, ""):
                raise ValueError(MalformedReason.ARTICLE_SCHEMA_INVALID)

        title = str(record.get("title", "")).strip()
        if not title:
            raise ValueError(MalformedReason.EMPTY_TITLE)

        content = str(record.get("content", "")).strip()
        if not content:
            raise ValueError(MalformedReason.EMPTY_CONTENT)

        return cls(
            schema_version=str(record["schema_version"]).strip(),
            article_id=str(record["article_id"]).strip(),
            source=str(record["source"]).strip(),
            category_cd=str(record["category_cd"]).strip(),
            title=title,
            content=content,
            url=str(record.get("url", "")).strip(),
            content_hash=str(record.get("content_hash", "")).strip(),
            batch_id=str(record["batch_id"]).strip(),
            run_attempt=int(record["run_attempt"]),
            published_at=_optional_text(record.get("published_at")),
        )

    @property
    def document_text(self) -> str:
        return f"{self.title}\n{self.content}"

    def to_extraction_record(
        self,
        keywords: list["ClassifiedKeyword"],
        event_signals: list["EventSignal"],
        review_required: bool,
        review_reasons: list[str],
        created_at: str,
    ) -> "KeywordExtractionRecord":
        return KeywordExtractionRecord(
            article_id=self.article_id,
            source=self.source,
            category_cd=self.category_cd,
            title=self.title,
            url=self.url,
            published_at=self.published_at,
            content_hash=self.content_hash,
            keywords=keywords,
            event_signals=event_signals,
            review_required=review_required,
            review_reasons=review_reasons,
            batch_id=self.batch_id,
            run_attempt=self.run_attempt,
            created_at=created_at,
        )


@dataclass(frozen=True)
class MorphToken:
    form: str
    tag: str


@dataclass(frozen=True)
class KeywordCandidate:
    text: str
    article_id: str
    title_occurrences: int = 0
    body_occurrences: int = 0
    importance_score: float = 0.0

    @property
    def total_occurrences(self) -> int:
        return self.title_occurrences + self.body_occurrences


@dataclass(frozen=True)
class ClassifiedKeyword:
    canonical_name: str
    matched_keyword: str
    node_type: str
    importance_score: float
    classification_confidence: float
    source: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "canonical_name": self.canonical_name,
            "matched_keyword": self.matched_keyword,
            "node_type": self.node_type,
            "importance_score": self.importance_score,
            "classification_confidence": self.classification_confidence,
            "source": self.source,
        }


@dataclass(frozen=True)
class EventSignal:
    action_type: str
    matched_text: str
    confidence: float
    source: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "action_type": self.action_type,
            "matched_text": self.matched_text,
            "confidence": self.confidence,
            "source": self.source,
        }


@dataclass(frozen=True)
class KeywordExtractionRecord:
    article_id: str
    source: str
    category_cd: str
    title: str
    url: str
    published_at: str | None
    content_hash: str
    keywords: list[ClassifiedKeyword]
    event_signals: list[EventSignal]
    review_required: bool
    review_reasons: list[str]
    batch_id: str
    run_attempt: int
    created_at: str
    schema_version: str = KEYWORD_EXTRACTION_SCHEMA_VERSION
    ranking_method: str = RANKING_METHOD

    @property
    def keyword_count(self) -> int:
        return len(self.keywords)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "article_id": self.article_id,
            "source": self.source,
            "category_cd": self.category_cd,
            "title": self.title,
            "url": self.url,
            "published_at": self.published_at,
            "content_hash": self.content_hash,
            "keywords": [keyword.to_dict() for keyword in self.keywords],
            "event_signals": [signal.to_dict() for signal in self.event_signals],
            "keyword_count": self.keyword_count,
            "ranking_method": self.ranking_method,
            "review_required": self.review_required,
            "review_reasons": self.review_reasons,
            "batch_id": self.batch_id,
            "run_attempt": self.run_attempt,
            "created_at": self.created_at,
        }


@dataclass(frozen=True)
class MalformedArticleRecord:
    article_id: str | None
    batch_id: str | None
    run_attempt: int | None
    reason_code: str
    message: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "article_id": self.article_id,
            "batch_id": self.batch_id,
            "run_attempt": self.run_attempt,
            "reason_code": self.reason_code,
            "message": self.message,
        }


@dataclass(frozen=True)
class ExtractionMetrics:
    total_article_count: int = 0
    success_article_count: int = 0
    malformed_article_count: int = 0
    review_required_count: int = 0
    total_keyword_count: int = 0
    status: str = field(init=False)

    def __post_init__(self) -> None:
        status = "PARTIAL_SUCCESS" if self.malformed_article_count else "SUCCESS"
        object.__setattr__(self, "status", status)

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_article_count": self.total_article_count,
            "success_article_count": self.success_article_count,
            "malformed_article_count": self.malformed_article_count,
            "review_required_count": self.review_required_count,
            "total_keyword_count": self.total_keyword_count,
            "status": self.status,
        }


def _optional_text(value: Any) -> str | None:
    text = str(value).strip() if value is not None else ""
    if not text:
        return None
    return text
