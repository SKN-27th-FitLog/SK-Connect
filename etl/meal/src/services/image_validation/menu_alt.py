from copy import deepcopy
from typing import Any


MENU_ALT_SOURCE_REVIEW_IMAGE_URL = "review_image_url"
MENU_ALT_SOURCE_REVIEW_IMAGE_URL_GROUP = "review_image_url_group"
MENU_NAME_SEPARATOR = ", "


def enrich_images_with_review_menu_alt(
    images: list[dict[str, Any]],
    reviews: Any,
) -> list[dict[str, Any]]:
    menu_names_by_image_url = build_review_image_menu_lookup(reviews)
    if not menu_names_by_image_url:
        return images

    enriched_images = list(images)
    for image_group in _group_images_by_validation_group(images):
        direct_menu_sets = _direct_menu_sets(image_group, menu_names_by_image_url)
        if len(direct_menu_sets) == 1:
            menu_names = list(direct_menu_sets[0])
            for position, image in image_group:
                enriched_images[position] = _with_menu_alt_text(
                    image,
                    menu_names,
                    source=MENU_ALT_SOURCE_REVIEW_IMAGE_URL_GROUP,
                )
            continue

        for position, image in image_group:
            menu_names = menu_names_by_image_url.get(_image_url(image))
            if not menu_names:
                continue
            enriched_images[position] = _with_menu_alt_text(
                image,
                menu_names,
                source=MENU_ALT_SOURCE_REVIEW_IMAGE_URL,
            )
    return enriched_images


def build_review_image_menu_lookup(reviews: Any) -> dict[str, list[str]]:
    if not isinstance(reviews, list):
        return {}

    lookup: dict[str, list[str]] = {}
    for review in reviews:
        if not isinstance(review, dict):
            continue

        menu_names = _clean_unique_texts(review.get("ordered_menus"))
        if not menu_names:
            continue

        for image_url in _clean_unique_texts(review.get("review_images")):
            existing = lookup.setdefault(image_url, [])
            for menu_name in menu_names:
                if menu_name not in existing:
                    existing.append(menu_name)
    return lookup


def _group_images_by_validation_group(
    images: list[dict[str, Any]],
) -> list[list[tuple[int, dict[str, Any]]]]:
    groups: dict[tuple[str, str], list[tuple[int, dict[str, Any]]]] = {}
    for position, image in enumerate(images):
        groups.setdefault(_image_group_key(position, image), []).append((position, image))
    return list(groups.values())


def _image_group_key(position: int, image: dict[str, Any]) -> tuple[str, str]:
    validation = image.get("validation") if isinstance(image, dict) else {}
    if isinstance(validation, dict):
        group_id = _clean_text(validation.get("group_id"))
        if group_id:
            return ("group", group_id)
    return ("image", str(position))


def _direct_menu_sets(
    image_group: list[tuple[int, dict[str, Any]]],
    menu_names_by_image_url: dict[str, list[str]],
) -> list[tuple[str, ...]]:
    menu_sets: list[tuple[str, ...]] = []
    for _, image in image_group:
        menu_names = menu_names_by_image_url.get(_image_url(image))
        if not menu_names:
            continue

        menu_set = tuple(menu_names)
        if menu_set not in menu_sets:
            menu_sets.append(menu_set)
    return menu_sets


def _with_menu_alt_text(
    image: dict[str, Any],
    menu_names: list[str],
    source: str,
) -> dict[str, Any]:
    data = deepcopy(image)
    validation = data.get("validation")
    if not isinstance(validation, dict):
        validation = {}

    validation["menu_names"] = menu_names
    validation["menu_alt_source"] = source
    validation["alt_text"] = MENU_NAME_SEPARATOR.join(menu_names)
    data["validation"] = validation
    return data


def _image_url(image: dict[str, Any]) -> str:
    return _clean_text(image.get("url")) if isinstance(image, dict) else ""


def _clean_unique_texts(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []

    cleaned_values: list[str] = []
    for value in values:
        cleaned = _clean_text(value)
        if cleaned and cleaned not in cleaned_values:
            cleaned_values.append(cleaned)
    return cleaned_values


def _clean_text(value: Any) -> str:
    return str(value or "").strip()
