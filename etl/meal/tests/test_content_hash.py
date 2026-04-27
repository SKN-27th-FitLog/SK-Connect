from src.core.utils.content_hash import build_content_hash


def test_content_hash_uses_canonical_json_rules():
    left = {
        "name": "  Test   Shop ",
        "tags": [{"b": "2", "a": ""}, {"a": "1", "b": None}],
    }
    right = {
        "tags": [{"b": None, "a": "1"}, {"a": None, "b": "2"}],
        "name": "Test Shop",
    }

    assert build_content_hash(left) == build_content_hash(right)
