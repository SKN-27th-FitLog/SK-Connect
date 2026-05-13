from collections.abc import Callable


def _is_blank_string(value: object) -> bool:
    return isinstance(value, str) and value.strip() == ""


def _merge_concat_value(existing_value: object, incoming_value: object) -> object:
    """concat 대상 필드 병합 규칙을 적용한다."""
    if existing_value is None:
        return incoming_value
    if incoming_value is None:
        return existing_value

    if _is_blank_string(existing_value):
        return incoming_value
    if _is_blank_string(incoming_value):
        return existing_value

    return f"{existing_value}, {incoming_value}"


def _merge_timestamp(
    target: dict,
    incoming: dict,
    key: str,
    reducer: Callable[[object, object], object],
) -> None:
    target_value = target.get(key)
    incoming_value = incoming.get(key)

    if target_value is None:
        target[key] = incoming_value
    elif incoming_value is not None:
        target[key] = reducer(target_value, incoming_value)


def apply_merge_rules(
    target: dict,
    incoming: dict,
    concat_keys: list[str],
    fill_if_none_keys: list[str],
) -> dict:
    """공통 merge 규칙 적용: 문자열 누적 + None 보강 + created/updated min/max."""
    for key in concat_keys:
        target[key] = _merge_concat_value(target.get(key), incoming.get(key))

    for key in fill_if_none_keys:
        if target.get(key) is None:
            target[key] = incoming.get(key)

    _merge_timestamp(target, incoming, "created_at", min)
    _merge_timestamp(target, incoming, "updated_at", max)

    return target
