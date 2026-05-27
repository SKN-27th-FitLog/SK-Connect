import json

from src.services.image_validation.models import (
    DroppedImage,
    ImageValidationDecision,
    ValidatedImage,
)


def test_validated_image_adds_group_metadata_and_alt_text_without_mutating_source():
    source = {"url": "https://cdn.example.com/food.webp", "category": "food"}

    image = ValidatedImage.from_source(
        source,
        group_id="imggrp-001",
        group_order=2,
        nearest_similarity=0.7341239,
        model_version="clip-ViT-B-32",
    )

    assert "validation" not in source
    assert image.data["url"] == source["url"]
    assert image.data["validation"]["status"] == "keep"
    assert image.data["validation"]["group_id"] == "imggrp-001"
    assert image.data["validation"]["group_order"] == 2
    assert image.data["validation"]["nearest_similarity"] == 0.734124
    assert image.data["validation"]["model_version"] == "clip-ViT-B-32"
    assert image.data["validation"]["alt_text"] == "식당 유사 이미지 그룹 imggrp-001 2번"


def test_dropped_image_records_reason_without_mutating_source():
    source = {"url": "https://cdn.example.com/noise.webp", "category": "food"}

    dropped = DroppedImage.from_source(
        source,
        reason="NO_SIMILAR_IMAGE_IN_STORE",
        nearest_similarity=0.4100002,
        model_version="clip-ViT-B-32",
    )

    assert "validation" not in source
    assert dropped.data["url"] == source["url"]
    assert dropped.data["validation"]["status"] == "drop"
    assert dropped.data["validation"]["reason"] == "NO_SIMILAR_IMAGE_IN_STORE"
    assert dropped.data["validation"]["nearest_similarity"] == 0.41
    assert dropped.data["validation"]["model_version"] == "clip-ViT-B-32"


def test_dropped_image_allows_missing_similarity():
    dropped = DroppedImage.from_source(
        {"url": "https://cdn.example.com/no-vector.webp"},
        reason="VECTORIZE_FAILED",
        nearest_similarity=None,
        model_version="clip-ViT-B-32",
    )

    assert dropped.data["validation"]["nearest_similarity"] is None


def test_image_validation_decision_to_record_is_json_serializable_summary():
    decision = ImageValidationDecision(
        kept_images=[{"url": "https://cdn.example.com/a.webp"}],
        dropped_images=[{"url": "https://cdn.example.com/b.webp"}],
        total_count=2,
        kept_count=1,
        dropped_count=1,
        model_version="clip-ViT-B-32",
    )

    record = decision.to_record()

    assert record == {
        "total_count": 2,
        "kept_count": 1,
        "dropped_count": 1,
        "model_version": "clip-ViT-B-32",
    }
    assert json.loads(json.dumps(record)) == record
