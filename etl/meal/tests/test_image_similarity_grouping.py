from src.services.image_validation.grouping import group_similar_images


def test_group_similar_images_keeps_only_images_in_three_image_groups():
    images = [
        {"url": "a"},
        {"url": "b"},
        {"url": "e"},
        {"url": "c"},
        {"url": "d"},
    ]
    vectors = {
        "a": [1.0, 0.0, 0.0],
        "b": [0.8, 0.2, 0.0],
        "e": [0.7, 0.3, 0.0],
        "c": [0.0, 1.0, 0.0],
        "d": [0.0, 0.0, 1.0],
    }

    decision = group_similar_images(
        images=images,
        vector_provider=lambda url: vectors[url],
        similarity_threshold=0.60,
        model_version="fake",
    )

    assert [image["url"] for image in decision.kept_images] == ["a", "b", "e"]
    assert [image["url"] for image in decision.dropped_images] == ["c", "d"]
    assert decision.kept_images[0]["validation"]["group_id"] == "imggrp-001"
    assert decision.kept_images[0]["validation"]["group_order"] == 1
    assert decision.kept_images[1]["validation"]["group_id"] == "imggrp-001"
    assert decision.kept_images[1]["validation"]["group_order"] == 2
    assert decision.kept_images[2]["validation"]["group_id"] == "imggrp-001"
    assert decision.kept_images[2]["validation"]["group_order"] == 3
    assert decision.kept_images[0]["validation"]["alt_text"] == "식당 유사 이미지 그룹 imggrp-001 1번"
    assert decision.dropped_images[0]["validation"]["reason"] == "NO_SIMILAR_IMAGE_IN_STORE"
    assert decision.to_record() == {
        "total_count": 5,
        "kept_count": 3,
        "dropped_count": 2,
        "model_version": "fake",
    }


def test_group_similar_images_drops_two_image_components_by_default():
    images = [{"url": "a"}, {"url": "b"}]
    vectors = {
        "a": [1.0, 0.0],
        "b": [0.8, 0.2],
    }

    decision = group_similar_images(
        images=images,
        vector_provider=lambda url: vectors[url],
        similarity_threshold=0.60,
        model_version="fake",
    )

    assert decision.kept_images == []
    assert [image["url"] for image in decision.dropped_images] == ["a", "b"]
    assert [image["validation"]["reason"] for image in decision.dropped_images] == [
        "NO_SIMILAR_IMAGE_IN_STORE",
        "NO_SIMILAR_IMAGE_IN_STORE",
    ]


def test_group_similar_images_drops_chain_components_without_two_direct_neighbors():
    images = [{"url": "a"}, {"url": "b"}, {"url": "c"}]
    vectors = {
        "a": [1.0, 0.0],
        "b": [0.8, 0.6],
        "c": [0.28, 0.96],
    }

    decision = group_similar_images(
        images=images,
        vector_provider=lambda url: vectors[url],
        similarity_threshold=0.60,
        model_version="fake",
    )

    assert decision.kept_images == []
    assert [image["url"] for image in decision.dropped_images] == ["a", "b", "c"]
    assert [image["validation"]["reason"] for image in decision.dropped_images] == [
        "NO_SIMILAR_IMAGE_IN_STORE",
        "NO_SIMILAR_IMAGE_IN_STORE",
        "NO_SIMILAR_IMAGE_IN_STORE",
    ]


def test_group_similar_images_assigns_group_ids_by_input_order():
    images = [
        {"url": "first-a"},
        {"url": "first-b"},
        {"url": "first-c"},
        {"url": "second-a"},
        {"url": "second-b"},
        {"url": "second-c"},
    ]
    vectors = {
        "first-a": [1.0, 0.0, 0.0],
        "first-b": [0.9, 0.1, 0.0],
        "first-c": [0.8, 0.2, 0.0],
        "second-a": [0.0, 1.0, 0.0],
        "second-b": [0.0, 0.9, 0.1],
        "second-c": [0.0, 0.8, 0.2],
    }

    decision = group_similar_images(
        images=images,
        vector_provider=lambda url: vectors[url],
        similarity_threshold=0.60,
        model_version="fake",
    )

    assert [
        (image["url"], image["validation"]["group_id"], image["validation"]["group_order"])
        for image in decision.kept_images
    ] == [
        ("first-a", "imggrp-001", 1),
        ("first-b", "imggrp-001", 2),
        ("first-c", "imggrp-001", 3),
        ("second-a", "imggrp-002", 1),
        ("second-b", "imggrp-002", 2),
        ("second-c", "imggrp-002", 3),
    ]


def test_group_similar_images_drops_singletons_per_call_without_cross_store_grouping():
    first_store = group_similar_images(
        images=[{"url": "shared-a"}],
        vector_provider=lambda url: [1.0, 0.0],
        similarity_threshold=0.60,
        model_version="fake",
    )
    second_store = group_similar_images(
        images=[{"url": "shared-b"}],
        vector_provider=lambda url: [1.0, 0.0],
        similarity_threshold=0.60,
        model_version="fake",
    )

    assert first_store.kept_images == []
    assert second_store.kept_images == []
    assert first_store.dropped_images[0]["validation"]["reason"] == "NO_SIMILAR_IMAGE_IN_STORE"
    assert second_store.dropped_images[0]["validation"]["reason"] == "NO_SIMILAR_IMAGE_IN_STORE"


def test_group_similar_images_records_missing_url_and_vectorize_failures():
    images = [
        {"url": ""},
        {"url": "broken"},
        {"url": "a"},
        {"url": "b"},
        {"url": "c"},
    ]

    def vector_provider(url):
        if url == "broken":
            raise OSError("download failed")
        return [1.0, 0.0]

    decision = group_similar_images(
        images=images,
        vector_provider=vector_provider,
        similarity_threshold=0.60,
        model_version="fake",
    )

    assert [image["url"] for image in decision.kept_images] == ["a", "b", "c"]
    assert [image["validation"]["reason"] for image in decision.dropped_images] == [
        "MISSING_IMAGE_URL",
        "VECTORIZE_FAILED",
    ]
    assert all(
        image["validation"]["nearest_similarity"] is None
        for image in decision.dropped_images
    )
