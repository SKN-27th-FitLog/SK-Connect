from __future__ import annotations

import json
import urllib.request
from dataclasses import dataclass

from kag_graph.extraction.models import ClassifiedKeyword, KeywordCandidate
from kag_graph.extraction.response_parser import ResponseParser


OLLAMA_GENERATE_URL = "http://localhost:11434/api/generate"


@dataclass(frozen=True)
class OllamaKeywordClassifier:
    model: str = "gemma"
    timeout_seconds: int = 20
    retry_count: int = 1
    endpoint_url: str = OLLAMA_GENERATE_URL

    def classify(
        self,
        article_id: str,
        candidates: list[KeywordCandidate],
        title: str,
        content: str,
    ) -> list[ClassifiedKeyword]:
        candidate_by_text = {candidate.text: candidate for candidate in candidates}
        payload = {
            "model": self.model,
            "prompt": self._prompt(article_id, candidates, title, content),
            "stream": False,
        }
        response_text = self._request(payload)
        parsed = ResponseParser().parse(response_text)
        keywords = parsed.get("keywords", [])
        if not isinstance(keywords, list):
            return []

        result: list[ClassifiedKeyword] = []
        for row in keywords:
            matched_keyword = str(row.get("matched_keyword", "")).strip()
            candidate = candidate_by_text.get(matched_keyword)
            if candidate is None:
                continue
            result.append(
                ClassifiedKeyword(
                    canonical_name=str(row.get("canonical_name", "")).strip(),
                    matched_keyword=matched_keyword,
                    node_type=str(row.get("node_type", "")).strip(),
                    importance_score=candidate.importance_score,
                    classification_confidence=float(row.get("classification_confidence", 0.0)),
                    source="llm",
                )
            )
        return result

    def _request(self, payload: dict[str, object]) -> str:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(
            self.endpoint_url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        last_error: Exception | None = None
        for _ in range(self.retry_count + 1):
            try:
                with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                    body = json.loads(response.read().decode("utf-8"))
                    return str(body.get("response", ""))
            except Exception as exc:
                last_error = exc
        raise RuntimeError("LLM classification failed") from last_error

    def _prompt(self, article_id: str, candidates: list[KeywordCandidate], title: str, content: str) -> str:
        candidate_text = "\n".join(f"- {candidate.text}" for candidate in candidates)
        return (
            "다음 IT 뉴스 keyword 후보를 Technology, Company, Event, Topic, Ignore 중 하나로 분류하라.\n"
            "새 keyword를 추출하지 말고 입력 후보만 분류하라.\n"
            'JSON 형식: {"article_id": "...", "keywords": [{"canonical_name": "...", '
            '"matched_keyword": "...", "node_type": "...", "classification_confidence": 0.0}]}\n'
            f"article_id: {article_id}\n"
            f"title: {title}\n"
            f"content: {content[:1500]}\n"
            f"candidates:\n{candidate_text}"
        )
