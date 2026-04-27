import hashlib
import json
import math
import re
from typing import Any, Iterable

HASH_VERSION = "sha256-canonical-json-v1"
HASH_FIELDS_VERSION = "meal-entity-fields-v1"


def _is_null_family(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, float) and math.isnan(value):
        return True
    if isinstance(value, str) and value.strip() == "":
        return True
    return False


def canonicalize(value: Any) -> Any:
    if _is_null_family(value):
        return None
    if isinstance(value, str):
        return re.sub(r"\s+", " ", value.strip())
    if isinstance(value, list):
        return sorted((canonicalize(item) for item in value), key=_sort_key)
    if isinstance(value, tuple):
        return canonicalize(list(value))
    if isinstance(value, dict):
        return {key: canonicalize(value[key]) for key in sorted(value)}
    return value


def _sort_key(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def build_content_hash(payload: Any) -> str:
    canonical_payload = canonicalize(payload)
    encoded = json.dumps(
        canonical_payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def pick_fields(data: dict[str, Any], fields: Iterable[str]) -> dict[str, Any]:
    return {field: data.get(field) for field in fields}
