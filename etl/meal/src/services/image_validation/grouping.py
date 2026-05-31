from collections.abc import Callable
from typing import Any

import numpy as np

from src.services.image_validation.models import (
    DroppedImage,
    ImageValidationDecision,
    ValidatedImage,
)
from src.services.image_validation.vectorizer import normalize_vector

DEFAULT_IMAGE_SIMILARITY_THRESHOLD = 0.60
DEFAULT_MIN_SIMILAR_IMAGE_GROUP_SIZE = 3
DROP_REASON_MISSING_IMAGE_URL = "MISSING_IMAGE_URL"
DROP_REASON_VECTORIZE_FAILED = "VECTORIZE_FAILED"
DROP_REASON_NO_SIMILAR_IMAGE_IN_STORE = "NO_SIMILAR_IMAGE_IN_STORE"


def group_similar_images(
    images: list[dict[str, Any]],
    vector_provider: Callable[[str], Any],
    similarity_threshold: float = DEFAULT_IMAGE_SIMILARITY_THRESHOLD,
    min_group_size: int = DEFAULT_MIN_SIMILAR_IMAGE_GROUP_SIZE,
    model_version: str = "unknown",
) -> ImageValidationDecision:
    valid_items: list[tuple[int, dict[str, Any], np.ndarray]] = []
    dropped_by_index: dict[int, dict[str, Any]] = {}

    for index, image in enumerate(images):
        url = _extract_url(image)
        if not url:
            dropped_by_index[index] = DroppedImage.from_source(
                image,
                reason=DROP_REASON_MISSING_IMAGE_URL,
                nearest_similarity=None,
                model_version=model_version,
            ).data
            continue

        try:
            vector = normalize_vector(vector_provider(url))
        except Exception:
            dropped_by_index[index] = DroppedImage.from_source(
                image,
                reason=DROP_REASON_VECTORIZE_FAILED,
                nearest_similarity=None,
                model_version=model_version,
            ).data
            continue

        valid_items.append((index, image, vector))

    similarities = _build_similarity_matrix(valid_items)
    components = _build_connected_components(similarities, similarity_threshold)

    kept_images: list[dict[str, Any]] = []
    group_number = 1
    for component in components:
        stable_component = _build_stable_component(
            component,
            similarities,
            similarity_threshold,
            min_group_size,
        )
        if len(stable_component) < min_group_size:
            for position in component:
                source_index, source, _ = valid_items[position]
                dropped_by_index[source_index] = DroppedImage.from_source(
                    source,
                    reason=DROP_REASON_NO_SIMILAR_IMAGE_IN_STORE,
                    nearest_similarity=_nearest_similarity(similarities, position),
                    model_version=model_version,
                ).data
            continue

        stable_positions = set(stable_component)
        for position in component:
            if position in stable_positions:
                continue
            source_index, source, _ = valid_items[position]
            dropped_by_index[source_index] = DroppedImage.from_source(
                source,
                reason=DROP_REASON_NO_SIMILAR_IMAGE_IN_STORE,
                nearest_similarity=_nearest_similarity(similarities, position),
                model_version=model_version,
            ).data

        group_id = f"imggrp-{group_number:03d}"
        for group_order, position in enumerate(stable_component, start=1):
            _, source, _ = valid_items[position]
            kept_images.append(
                ValidatedImage.from_source(
                    source,
                    group_id=group_id,
                    group_order=group_order,
                    nearest_similarity=_nearest_similarity(
                        similarities,
                        position,
                        peer_positions=component,
                    ),
                    model_version=model_version,
                ).data
            )
        group_number += 1

    dropped_images = [
        dropped_by_index[index]
        for index in sorted(dropped_by_index)
    ]

    return ImageValidationDecision(
        kept_images=kept_images,
        dropped_images=dropped_images,
        total_count=len(images),
        kept_count=len(kept_images),
        dropped_count=len(dropped_images),
        model_version=model_version,
    )


def _extract_url(image: dict[str, Any]) -> str:
    return str(image.get("url", "")).strip()


def _build_similarity_matrix(
    valid_items: list[tuple[int, dict[str, Any], np.ndarray]],
) -> np.ndarray:
    if not valid_items:
        return np.zeros((0, 0), dtype=float)

    matrix = np.stack([vector for _, _, vector in valid_items], axis=0)
    return matrix @ matrix.T


def _build_connected_components(
    similarities: np.ndarray,
    similarity_threshold: float,
) -> list[list[int]]:
    components: list[list[int]] = []
    visited: set[int] = set()

    # 입력 순서 기준으로 연결 컴포넌트를 만들어 group id를 안정적으로 부여한다.
    for start in range(similarities.shape[0]):
        if start in visited:
            continue

        stack = [start]
        component: list[int] = []
        visited.add(start)

        while stack:
            current = stack.pop()
            component.append(current)
            for neighbor in range(similarities.shape[0]):
                if neighbor in visited:
                    continue
                if float(similarities[current, neighbor]) < similarity_threshold:
                    continue
                visited.add(neighbor)
                stack.append(neighbor)

        components.append(sorted(component))

    return components


def _build_stable_component(
    component: list[int],
    similarities: np.ndarray,
    similarity_threshold: float,
    min_group_size: int,
) -> list[int]:
    required_neighbor_count = max(min_group_size - 1, 0)
    if required_neighbor_count == 0:
        return component

    remaining = set(component)
    changed = True
    while changed:
        changed = False
        unstable_positions = [
            position
            for position in sorted(remaining)
            if _similar_peer_count(
                similarities,
                position,
                remaining,
                similarity_threshold,
            ) < required_neighbor_count
        ]
        if unstable_positions:
            remaining.difference_update(unstable_positions)
            changed = True

    return [position for position in component if position in remaining]


def _similar_peer_count(
    similarities: np.ndarray,
    position: int,
    peer_positions: set[int],
    similarity_threshold: float,
) -> int:
    return sum(
        1
        for peer_position in peer_positions
        if peer_position != position
        and float(similarities[position, peer_position]) >= similarity_threshold
    )


def _nearest_similarity(
    similarities: np.ndarray,
    position: int,
    peer_positions: list[int] | None = None,
) -> float | None:
    if similarities.shape[0] < 2:
        return None

    candidates = peer_positions or list(range(similarities.shape[0]))
    scores = [
        float(similarities[position, candidate])
        for candidate in candidates
        if candidate != position
    ]
    if not scores:
        return None
    return max(scores)
