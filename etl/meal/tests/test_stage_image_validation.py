from copy import deepcopy

from src.projects.image_validation.stage_image_validation import StageImageValidation


def test_stage_image_validation_filters_each_record_independently():
    vectors = {
        "store1-a": [1.0, 0.0],
        "store1-b": [0.8, 0.2],
        "store1-c": [0.7, 0.3],
        "store2-a": [0.0, 1.0],
        "store2-b": [0.2, 0.8],
        "store2-c": [0.3, 0.7],
    }
    stage = StageImageValidation(
        vector_provider=lambda url: vectors[url],
        similarity_threshold=0.60,
        model_version="fake",
    )
    records = [
        {
            "batch_id": "batch",
            "run_attempt": 1,
            "stage": "validation_normalization",
            "entity_id": "store-1",
            "store": {"name": "Store One"},
            "images": [{"url": "store1-a"}, {"url": "store1-b"}, {"url": "store1-c"}],
        },
        {
            "batch_id": "batch",
            "run_attempt": 1,
            "stage": "validation_normalization",
            "entity_id": "store-2",
            "store": {"name": "Store Two"},
            "images": [{"url": "store2-a"}, {"url": "store2-b"}, {"url": "store2-c"}],
        },
    ]

    validated = stage.execute(records, batch_id="batch", category_cd="SC01", run_attempt=1)

    assert len(validated) == 2
    assert validated[0]["stage"] == "image_validation"
    assert [image["url"] for image in validated[0]["images"]] == ["store1-a", "store1-b", "store1-c"]
    assert [image["url"] for image in validated[1]["images"]] == ["store2-a", "store2-b", "store2-c"]
    assert validated[0]["dropped_images"] == []
    assert validated[1]["dropped_images"] == []
    assert validated[0]["image_validation"]["kept_count"] == 3
    assert validated[1]["image_validation"]["kept_count"] == 3


def test_stage_image_validation_does_not_mutate_input_records():
    stage = StageImageValidation(
        vector_provider=lambda url: [1.0, 0.0],
        similarity_threshold=0.60,
        model_version="fake",
    )
    records = [
        {
            "batch_id": "batch",
            "run_attempt": 1,
            "stage": "validation_normalization",
            "entity_id": "store-1",
            "images": [{"url": "a"}, {"url": "b"}],
            "nested": {"value": 1},
        }
    ]
    original = deepcopy(records)

    validated = stage.execute(records, batch_id="batch", category_cd="SC01", run_attempt=1)

    assert records == original
    assert validated is not records
    assert validated[0] is not records[0]
    assert validated[0]["images"] is not records[0]["images"]


def test_stage_image_validation_propagates_single_review_menu_to_similar_group_alt_text():
    stage = StageImageValidation(
        vector_provider=lambda url: [1.0, 0.0],
        similarity_threshold=0.60,
        model_version="fake",
    )
    records = [
        {
            "batch_id": "batch",
            "run_attempt": 1,
            "stage": "validation_normalization",
            "entity_id": "store-1",
            "reviews": [
                {
                    "author": "food-user",
                    "ordered_menus": ["순대국"],
                    "review_images": ["image-a"],
                },
            ],
            "images": [
                {"url": "image-a", "nickname": "food-user"},
                {"url": "image-b", "nickname": "other-user"},
                {"url": "image-c", "nickname": "food-user"},
            ],
        }
    ]

    validated = stage.execute(records, batch_id="batch", category_cd="SC01", run_attempt=1)

    first, second, third = validated[0]["images"]
    assert first["validation"]["menu_names"] == ["순대국"]
    assert second["validation"]["menu_names"] == ["순대국"]
    assert third["validation"]["menu_names"] == ["순대국"]
    assert first["validation"]["menu_alt_source"] == "review_image_url_group"
    assert second["validation"]["menu_alt_source"] == "review_image_url_group"
    assert third["validation"]["menu_alt_source"] == "review_image_url_group"
    assert first["validation"]["alt_text"] == "순대국"
    assert second["validation"]["alt_text"] == "순대국"
    assert third["validation"]["alt_text"] == "순대국"


def test_stage_image_validation_does_not_propagate_conflicting_group_menu_names():
    stage = StageImageValidation(
        vector_provider=lambda url: [1.0, 0.0],
        similarity_threshold=0.60,
        model_version="fake",
    )
    records = [
        {
            "batch_id": "batch",
            "run_attempt": 1,
            "stage": "validation_normalization",
            "entity_id": "store-1",
            "reviews": [
                {
                    "author": "food-user",
                    "ordered_menus": ["순대국"],
                    "review_images": ["image-a"],
                },
                {
                    "author": "meal-user",
                    "ordered_menus": ["수육"],
                    "review_images": ["image-b"],
                },
            ],
            "images": [
                {"url": "image-a", "nickname": "food-user"},
                {"url": "image-b", "nickname": "meal-user"},
                {"url": "image-c", "nickname": "other-user"},
            ],
        }
    ]

    validated = stage.execute(records, batch_id="batch", category_cd="SC01", run_attempt=1)

    first, second, third = validated[0]["images"]
    assert first["validation"]["menu_names"] == ["순대국"]
    assert first["validation"]["menu_alt_source"] == "review_image_url"
    assert first["validation"]["alt_text"] == "순대국"
    assert second["validation"]["menu_names"] == ["수육"]
    assert second["validation"]["menu_alt_source"] == "review_image_url"
    assert second["validation"]["alt_text"] == "수육"
    assert "menu_names" not in third["validation"]
    assert third["validation"]["alt_text"] == "식당 유사 이미지 그룹 imggrp-001 3번"


def test_stage_image_validation_preserves_existing_fields_and_drops_singletons():
    stage = StageImageValidation(
        vector_provider=lambda url: [1.0, 0.0],
        similarity_threshold=0.60,
        model_version="fake",
    )
    records = [
        {
            "batch_id": "batch",
            "run_attempt": 1,
            "stage": "validation_normalization",
            "entity_id": "store-1",
            "store": {"name": "Store One"},
            "menus": [{"name": "Soup"}],
            "reviews": [{"content": "ok"}],
            "images": [{"url": "only-one"}],
        }
    ]

    validated = stage.execute(records, batch_id="batch", category_cd="SC01", run_attempt=1)

    assert validated[0]["store"] == records[0]["store"]
    assert validated[0]["menus"] == records[0]["menus"]
    assert validated[0]["reviews"] == records[0]["reviews"]
    assert validated[0]["images"] == []
    assert [image["url"] for image in validated[0]["dropped_images"]] == ["only-one"]
    assert validated[0]["image_validation"] == {
        "total_count": 1,
        "kept_count": 0,
        "dropped_count": 1,
        "model_version": "fake",
    }
