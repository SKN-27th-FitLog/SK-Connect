from functools import lru_cache

from common.logging_config import set_logging
from kiwipiepy import Kiwi

logger = set_logging()


@lru_cache(maxsize=1)
def get_kiwi() -> Kiwi:
    return Kiwi()


@lru_cache(maxsize=1)
def get_morph_config() -> dict:
    """키워드 시그니처 추출에 사용할 형태소 태그 규칙을 반환한다."""
    return {
        "noun_tags": {"NNG", "NNP", "NNB"},
        "topic_noun_tags": {"NNG", "NNP"},
        "noun_prefix_tags": {"XPN"},
        "noun_suffix_tags": {"XSN"},
        "predicate_tags": {"VV", "VA", "VX"},
        "verbalizing_tags": {"XSV", "XSA"},
        "generic_predicate_stems": {"있", "없", "하", "되", "이", "같"},
    }


@lru_cache(maxsize=4096)
def extract_keyword_signatures(keyword: str) -> tuple[str, ...]:
    """형태소 분석으로 키워드의 의미 시그니처(술어 기반)를 추출한다."""
    text = str(keyword or "").strip()
    if not text:
        return ()
    try:
        tokens = get_kiwi().tokenize(text)
    except Exception as e:
        logger.error(f"extract_keyword_signatures | tokenize fail | keyword={keyword} | error={e}")
        return ()

    config = get_morph_config()
    signatures: list[str] = []
    pending_noun_parts: list[str] = []
    pending_mag: str | None = None
    pending_xr: str | None = None

    for token in tokens:
        form = token.form
        tag = token.tag

        if tag in config["noun_prefix_tags"] or tag in config["noun_tags"]:
            pending_noun_parts.append(form)
            pending_mag = None
            pending_xr = None
            continue

        if tag in config["noun_suffix_tags"] and pending_noun_parts:
            pending_noun_parts.append(form)
            continue

        if tag == "MAG":
            pending_mag = form
            continue

        if tag == "XR":
            pending_xr = form
            continue

        if tag in config["verbalizing_tags"]:
            if pending_xr:
                signatures.append(f"{pending_xr}{form}다")
                pending_xr = None
                pending_mag = None
                pending_noun_parts = []
                continue
            if pending_mag:
                signatures.append(f"{pending_mag}{form}다")
                pending_mag = None
                continue
            if pending_noun_parts:
                noun = "".join(pending_noun_parts)
                pending_noun_parts = []
                signatures.append(f"{noun}{form}다")
                continue
            continue

        if tag == "VCP":
            if pending_mag:
                signatures.append(f"{pending_mag}이다")
                pending_mag = None
                pending_noun_parts = []
                pending_xr = None
                continue
            if pending_noun_parts:
                noun = "".join(pending_noun_parts)
                pending_noun_parts = []
                pending_xr = None
                signatures.append(f"{noun}이다")
                continue
            continue

        if tag in config["predicate_tags"]:
            if form in config["generic_predicate_stems"] and pending_noun_parts:
                noun = "".join(pending_noun_parts)
                signatures.append(f"{noun}_{form}다")
                pending_noun_parts = []
                pending_mag = None
                pending_xr = None
                continue
            signatures.append(f"{form}다")
            pending_noun_parts = []
            pending_mag = None
            pending_xr = None
            continue

        if tag.startswith("J") or tag.startswith("E"):
            pending_noun_parts = []
            pending_mag = None
            pending_xr = None

    if not signatures and pending_noun_parts:
        signatures.append("".join(pending_noun_parts))

    return tuple(signatures)


@lru_cache(maxsize=4096)
def extract_keyword_nouns(keyword: str) -> tuple[str, ...]:
    """키워드에서 등장한 일반/고유 명사 어절을 순서대로 추출한다."""
    text = str(keyword or "").strip()
    if not text:
        return ()
    try:
        tokens = get_kiwi().tokenize(text)
    except Exception as e:
        logger.error(f"extract_keyword_nouns | tokenize fail | keyword={keyword} | error={e}")
        return ()
    config = get_morph_config()
    return tuple(token.form for token in tokens if token.tag in config["topic_noun_tags"])


@lru_cache(maxsize=4096)
def extract_keyword_actions(keyword: str) -> tuple[str, ...]:
    """명사/부사에서 파생된 행동·의도 표현만 추출한다."""
    text = str(keyword or "").strip()
    if not text:
        return ()
    try:
        tokens = get_kiwi().tokenize(text)
    except Exception as e:
        logger.error(f"extract_keyword_actions | tokenize fail | keyword={keyword} | error={e}")
        return ()

    config = get_morph_config()
    actions = []
    nouns = []
    has_predicate_token = False
    pending_noun_parts = []
    pending_mag = None
    pending_xr = None
    for token in tokens:
        form = token.form
        tag = token.tag
        if tag in config["topic_noun_tags"]:
            nouns.append(form)
        if tag in config["noun_prefix_tags"] or tag in config["noun_tags"]:
            pending_noun_parts.append(form)
            pending_mag = None
            pending_xr = None
            continue
        if tag in config["noun_suffix_tags"] and pending_noun_parts:
            pending_noun_parts.append(form)
            continue
        if tag == "MAG":
            pending_mag = form
            continue
        if tag == "XR":
            pending_xr = form
            continue
        if tag in config["verbalizing_tags"]:
            has_predicate_token = True
            if pending_xr:
                actions.append(f"{pending_xr}{form}다")
                pending_xr = None
                pending_mag = None
                pending_noun_parts = []
                continue
            if pending_mag:
                actions.append(f"{pending_mag}{form}다")
                pending_mag = None
                continue
            if pending_noun_parts:
                actions.append(f"{''.join(pending_noun_parts)}{form}다")
                pending_noun_parts = []
                continue
            continue
        if tag == "VV":
            has_predicate_token = True
            if pending_mag:
                actions.append(f"{pending_mag}{form}다")
            pending_noun_parts = []
            pending_mag = None
            pending_xr = None
            continue
        if tag in config["predicate_tags"]:
            has_predicate_token = True
            pending_noun_parts = []
            pending_mag = None
            pending_xr = None
            continue
        if tag == "VCP":
            has_predicate_token = True
            pending_noun_parts = []
            pending_mag = None
            pending_xr = None
            continue
        if tag.startswith("J") or tag.startswith("E"):
            pending_noun_parts = []
            pending_mag = None
            pending_xr = None
    if not actions and not has_predicate_token and nouns:
        actions.append("".join(nouns))
    return tuple(actions)


@lru_cache(maxsize=4096)
def keyword_starts_with_noun(keyword: str) -> bool:
    """첫 의미 단위가 명사 계열인지 확인한다."""
    text = str(keyword or "").strip()
    if not text:
        return False
    try:
        tokens = get_kiwi().tokenize(text)
    except Exception as e:
        logger.error(f"keyword_starts_with_noun | tokenize fail | keyword={keyword} | error={e}")
        return False
    config = get_morph_config()
    for token in tokens:
        if token.tag.startswith("J") or token.tag.startswith("E"):
            continue
        return token.tag in config["noun_tags"] or token.tag in config["noun_prefix_tags"]
    return False


@lru_cache(maxsize=4096)
def keyword_has_predicate_token(keyword: str) -> bool:
    """키워드 안에 실제 술어/파생 술어가 있는지 확인한다."""
    text = str(keyword or "").strip()
    if not text:
        return False
    try:
        tokens = get_kiwi().tokenize(text)
    except Exception as e:
        logger.error(f"keyword_has_predicate_token | tokenize fail | keyword={keyword} | error={e}")
        return False
    config = get_morph_config()
    for token in tokens:
        if token.tag in config["predicate_tags"]:
            return True
        if token.tag in config["verbalizing_tags"]:
            return True
        if token.tag == "VCP":
            return True
    return False


def keyword_has_topic(keyword: str) -> bool:
    """대상어가 앞에 붙은 키워드인지 판단한다."""
    if is_nominal_predicate_statement(keyword):
        return False
    return (
        keyword_starts_with_noun(keyword)
        and keyword_has_predicate_token(keyword)
        and bool(extract_keyword_nouns(keyword))
    )


def keyword_topic_anchors(keyword: str) -> set:
    """대상어 그룹핑에 사용할 대표 명사를 반환한다."""
    nouns = extract_keyword_nouns(keyword)
    if keyword_has_topic(keyword) and nouns:
        return {nouns[0]}
    return set()


@lru_cache(maxsize=4096)
def is_nominal_predicate_statement(keyword: str) -> bool:
    """명사 하나가 지정사로 서술된 평가 표현인지 확인한다."""
    text = str(keyword or "").strip()
    if not text:
        return False
    try:
        tokens = get_kiwi().tokenize(text)
    except Exception as e:
        logger.error(f"is_nominal_predicate_statement | tokenize fail | keyword={keyword} | error={e}")
        return False

    config = get_morph_config()
    nouns = []
    has_copula = False
    has_other_predicate = False
    for token in tokens:
        if token.tag in config["topic_noun_tags"]:
            nouns.append(token.form)
            continue
        if token.tag == "VCP":
            has_copula = True
            continue
        if token.tag in config["predicate_tags"] or token.tag in config["verbalizing_tags"]:
            has_other_predicate = True
    return has_copula and not has_other_predicate and len(nouns) == 1


def keyword_signal_values(
    predicates: set,
    actions: set,
    nouns: set,
) -> set:
    """키워드 병합에 쓸 형태소 기반 신호를 모은다."""
    values = {
        str(value).strip()
        for value in predicates | actions | nouns
        if str(value).strip()
    }
    values |= {value[:-2] for value in values if value.endswith("이다")}
    return values


def has_containment_signal(left_values: set, right_values: set, min_length: int = 2) -> bool:
    """복합명사/복합술어처럼 한 신호가 다른 신호를 포함하는지 확인한다."""
    for left in left_values:
        for right in right_values:
            if left == right:
                continue
            shorter, longer = sorted((left, right), key=len)
            if len(shorter) < min_length:
                continue
            if shorter in longer:
                return True
    return False
