from __future__ import annotations

import json
import re
from typing import Any

from kag_graph.extraction.models import MalformedReason


class ResponseParser:
    def parse(self, response_text: str) -> dict[str, Any]:
        for candidate in (response_text, self._extract_json_block(response_text)):
            if not candidate:
                continue
            try:
                parsed = json.loads(candidate)
            except json.JSONDecodeError:
                continue
            if isinstance(parsed, dict):
                return parsed
        raise ValueError(MalformedReason.LLM_RESPONSE_PARSE_FAILED)

    def _extract_json_block(self, response_text: str) -> str | None:
        match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", response_text, re.DOTALL)
        if match is None:
            return None
        return match.group(1)
