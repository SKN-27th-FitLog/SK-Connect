from src.projects.process.stage3_validation_normalization import Stage3ValidationNormalization


class FakeCodeRepository:
    def preload(self):
        pass

    def get_address_info(self, key):
        return {"address_cd": key, "name": "서울"}

    def get_all_addresses(self):
        return {"서울": {"address_cd": "LA01", "name": "서울"}}

    def get_shop_code(self, key):
        return "SC01"


class FakeSnapshotRepository:
    def find_snapshot_by_dedup_key(self, dedup_key):
        return None


def test_stage3_outputs_entity_hash_contract():
    stage = Stage3ValidationNormalization(
        code_repository=FakeCodeRepository(),
        snapshot_repository=FakeSnapshotRepository(),
    )
    candidates = [
        {
            "entity_id": "LA01",
            "entity_ref": {"target_id": "target-1"},
            "shop": {
                "name": "테스트 식당",
                "full_address": "서울 강남구",
                "rating": 4.2,
                "source_platform": "DiningCode",
                "source_internal_id": "dc-1",
                "canonical_url": "https://example.test/shop/1",
            },
            "menus": [{"name": "김밥", "price": 4000}],
            "reviews": [{"content": "좋아요", "rating": 5, "visited_at": "2026-04-27"}],
            "images": [{"url": "https://example.test/image.jpg"}],
        }
    ]

    result = stage.execute(candidates, "20260427_SC01_001", "SC01")

    assert result[0]["store_content_hash"]
    assert result[0]["menu_content_hash"]
    assert result[0]["review_content_hash"]
    assert result[0]["image_content_hash"]
    assert result[0]["previous_store_content_hash"] is None
    assert result[0]["is_changed"] is True
    assert result[0]["changed_fields"] == ["store", "menu", "review", "image"]
