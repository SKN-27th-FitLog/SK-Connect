def apply_merge_rules(
    target: dict,
    incoming: dict,
    concat_keys: list[str],
    fill_if_none_keys: list[str],
) -> dict:
    """공통 merge 규칙 적용: 누적 + 대입 + created/updated min/max"""
    for k in concat_keys:
        existing = target.get(k)
        value = incoming.get(k)
        if existing is None:
            target[k] = value
            continue
        if value is None:
            continue
        target[k] = str(existing) + ', ' + str(value)

    for k in fill_if_none_keys:
        if target.get(k) is None:
            target[k] = incoming.get(k)

    if target.get('created_at') is None:
        target['created_at'] = incoming.get('created_at')
    elif incoming.get('created_at') is not None:
        target['created_at'] = min(target['created_at'], incoming['created_at'])

    if target.get('updated_at') is None:
        target['updated_at'] = incoming.get('updated_at')
    elif incoming.get('updated_at') is not None:
        target['updated_at'] = max(target['updated_at'], incoming['updated_at'])

    return target
