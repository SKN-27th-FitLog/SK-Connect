from src.core.storage.jsonl_writer import JsonlWriter
from src.projects.process.stage3_validation_normalization import Stage3ValidationNormalization


class FakeCodeRepository:
    def preload(self):
        pass

    def clear_cache(self):
        pass

    def get_address_info(self, address_cd):
        return None

    def get_all_addresses(self):
        return {}

    def get_shop_code(self, category_cd):
        return category_cd


class FakeSnapshotRepository:
    def bulk_find_snapshots(self, dedup_keys):
        return {}


def test_stage3_adds_menu_normalization_fields_without_changing_raw_name(monkeypatch):
    monkeypatch.setattr(JsonlWriter, "write", lambda *args, **kwargs: None)
    stage = Stage3ValidationNormalization(
        code_repository=FakeCodeRepository(),
        snapshot_repository=FakeSnapshotRepository(),
    )
    candidates = [
        {
            "entity_id": "store-001",
            "entity_ref": {"target_id": "target-001"},
            "shop": {
                "name": "제육집",
                "full_address": "서울 강남구",
                "rating": 4.0,
                "source_platform": "DiningCode",
                "source_internal_id": "store-001",
                "canonical_url": "https://example.com/pork",
            },
            "menus": [{"name": "매콤 직화 제육 정식 2인", "price": 12000}],
            "reviews": [],
            "images": [],
        }
    ]

    result = stage.execute(candidates, batch_id="20260512_SC01_001", category_cd="SC01")

    menu = result[0]["menus"][0]
    assert menu["name"] == "매콤 직화 제육 정식 2인"
    assert menu["raw_menu_name"] == "매콤 직화 제육 정식 2인"
    assert menu["display_menu_name"] == "매콤 직화 제육 정식 2인"
    assert menu["normalized_name"] == "제육볶음"
    assert menu["canonical_name"] == "제육볶음"
    assert menu["recipe_search_keyword"] == "제육볶음"
    assert menu["menu_confidence"] >= 0.88
    assert menu["menu_normalization_status"] == "NORMALIZED"
    assert menu["normalization_method"] == "RULE_SIMILARITY"


def test_stage3_marks_low_confidence_menu_without_recipe_keyword(monkeypatch):
    monkeypatch.setattr(JsonlWriter, "write", lambda *args, **kwargs: None)
    stage = Stage3ValidationNormalization(
        code_repository=FakeCodeRepository(),
        snapshot_repository=FakeSnapshotRepository(),
    )
    candidates = [
        {
            "entity_id": "store-002",
            "entity_ref": {"target_id": "target-002"},
            "shop": {
                "name": "한상집",
                "full_address": "서울 강남구",
                "rating": 4.0,
                "source_platform": "DiningCode",
                "source_internal_id": "store-002",
                "canonical_url": "https://example.com/unknown",
            },
            "menus": [{"name": "시그니처 한상", "price": 15000}],
            "reviews": [],
            "images": [],
        }
    ]

    result = stage.execute(candidates, batch_id="20260512_SC01_001", category_cd="SC01")

    menu = result[0]["menus"][0]
    assert menu["raw_menu_name"] == "시그니처 한상"
    assert menu["normalized_name"] is None
    assert menu["canonical_name"] is None
    assert menu["recipe_search_keyword"] is None
    assert menu["menu_confidence"] < 0.70
    assert menu["menu_normalization_status"] == "LOW_CONFIDENCE"
