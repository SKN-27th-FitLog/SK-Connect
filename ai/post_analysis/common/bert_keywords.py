"""원문 content 전처리 + 2~3어절 슬라이딩 + BERT 감성 점수로 keywords 추출.

DB 배치 진입점은 ``analyze_keywords.py``의 ``analyze_keywords()``이다.
"""

from __future__ import annotations

from dataclasses import dataclass

from common.bert_tokenizer import BertTokenizer
from common.constant import BertKeywords, SentimentLabel, SentimentResultKey


@dataclass(frozen=True)
class SpanCandidate:
    """어절 인덱스 구간과 BERT 점수를 담는 span 후보.

    Note:
        함수 유형: A — 순수 데이터 구조
        안전성: Level 0
    """

    span_text: str
    token_start: int
    token_end: int
    score: float


def _preprocess_content(text: str) -> str:
    """마침표→공백, 특수문자→공백, 연속 공백 축소.

    Note:
        함수 유형: A — 순수 계산
        안전성: Level 0
    """
    normalized = text.replace(".", " ").replace("。", " ")
    normalized = BertKeywords.NON_WORD_CHARS.sub(" ", normalized)
    return BertKeywords.MULTI_SPACE.sub(" ", normalized).strip()


def _is_standalone_jamo_token(token: str) -> bool:
    """자음·모음만으로 된 어절(예: ㅠ, ㅋ) 여부.

    Note:
        함수 유형: C — 검증
        안전성: Level 0
    """
    return bool(BertKeywords.STANDALONE_JAMO_TOKEN.fullmatch(token))


def _is_sentiment_shaped_token(token: str) -> bool:
    """감성 어미·형태로 보이는 짧은 어절만 opposite 검사 대상 (메뉴명 등 제외).

    Note:
        함수 유형: C — 검증
        안전성: Level 0
    """
    if len(token) > BertKeywords.TOKEN_OPPOSITE_MAX_LEN:
        return False
    return bool(BertKeywords.SENTIMENT_SHAPED_TOKEN.search(token))


def _is_within_token_len(
    token: str, max_len: int = BertKeywords.MAX_TOKEN_LEN
) -> bool:
    """어절 글자 수가 상한 이내인지.

    Note:
        함수 유형: C — 검증
        안전성: Level 0
    """
    return len(token) <= max_len


def _is_within_span_chars(
    span_text: str, max_chars: int = BertKeywords.MAX_SPAN_CHARS
) -> bool:
    """span 전체 글자 수가 상한 이내인지.

    Note:
        함수 유형: C — 검증
        안전성: Level 0
    """
    return len(span_text) <= max_chars


def _preprocessed_tokens(text: str) -> list[str]:
    """전처리 후 split — 자음·모음 단독 어절 제외.

    Note:
        함수 유형: A+B — 전처리 + 토큰 필터
        안전성: Level 0
    """
    preprocessed = _preprocess_content(text)
    if not preprocessed:
        return []
    return [
        token
        for token in preprocessed.split()
        if token.strip()
        and not _is_standalone_jamo_token(token)
        and _is_within_token_len(token)
    ]


def _slide_span_candidates(
    tokens: list[str],
    *,
    min_window: int = BertKeywords.MIN_WINDOW,
    max_window: int = BertKeywords.MAX_WINDOW,
) -> list[tuple[str, int, int]]:
    """2~3 어절 sliding window 후보 (span_text, token_start, token_end).

    Note:
        함수 유형: A — 순수 계산
        안전성: Level 0
        불변 규칙: 어절 수 < min_window 이면 빈 목록
    """
    if len(tokens) < min_window:
        return []

    candidates: list[tuple[str, int, int]] = []
    for win in range(min_window, max_window + 1):
        if len(tokens) < win:
            continue
        for i in range(len(tokens) - win + 1):
            end = i + win
            candidates.append((" ".join(tokens[i:end]), i, end))
    return candidates


def _span_target_score(result: dict, sentimental: str) -> float | None:
    """행 sentimental과 예측 label이 일치할 때만 해당 방향 score 반환.

    Note:
        함수 유형: A+C — 점수 선택 + label 일치 검증
        안전성: Level 0
        불변 규칙: label 불일치 시 None
    """
    sk = SentimentResultKey
    predicted = result[sk.SENTIMENTAL.value]
    if predicted != sentimental:
        return None
    if sentimental == SentimentLabel.POSITIVE.value:
        return float(result[sk.POSITIVE_SCORE.value])
    if sentimental == SentimentLabel.NEGATIVE.value:
        return float(result[sk.NEGATIVE_SCORE.value])
    return None


def _opposite_sentiment(sentimental: str) -> str:
    """긍·부정 라벨을 반대쪽으로 바꾼다.

    Note:
        함수 유형: A — 순수 계산
        안전성: Level 0
    """
    if sentimental == SentimentLabel.POSITIVE.value:
        return SentimentLabel.NEGATIVE.value
    return SentimentLabel.POSITIVE.value


def _token_opposite_score(result: dict, sentimental: str) -> float:
    """행 sentimental 기준 반대 방향 softmax 점수.

    Note:
        함수 유형: A — 순수 계산
        안전성: Level 0
    """
    sk = SentimentResultKey
    if sentimental == SentimentLabel.POSITIVE.value:
        return float(result[sk.NEGATIVE_SCORE.value])
    return float(result[sk.POSITIVE_SCORE.value])


def _token_same_direction_score(result: dict, sentimental: str) -> float:
    """행 sentimental과 같은 방향 softmax 점수.

    Note:
        함수 유형: A — 순수 계산
        안전성: Level 0
    """
    sk = SentimentResultKey
    if sentimental == SentimentLabel.POSITIVE.value:
        return float(result[sk.POSITIVE_SCORE.value])
    return float(result[sk.NEGATIVE_SCORE.value])


def _token_is_opposite_sentiment(result: dict, sentimental: str) -> bool:
    """단독 BERT 결과가 행 sentimental과 반대이고, score·margin 기준을 만족하면 True.

    Note:
        함수 유형: C — 검증
        안전성: Level 0
        불변 규칙: ``BertKeywords.TOKEN_OPPOSITE_*`` 임계값 적용
    """
    if result[SentimentResultKey.SENTIMENTAL.value] != _opposite_sentiment(sentimental):
        return False
    opposite_score = _token_opposite_score(result, sentimental)
    if opposite_score < BertKeywords.TOKEN_OPPOSITE_THRESHOLD:
        return False
    margin = opposite_score - _token_same_direction_score(result, sentimental)
    return (
        margin >= BertKeywords.TOKEN_OPPOSITE_MARGIN
        or opposite_score >= BertKeywords.TOKEN_OPPOSITE_HIGH
    )


def _get_token_sentiment(
    token: str,
    classifier: BertTokenizer,
    cache: dict[str, dict],
) -> dict:
    """어절 단위 BERT 감성 결과를 캐시 조회·저장한다.

    Note:
        함수 유형: A+E — 캐시 + BERT 추론 위임
        안전성: Level 1 — ``predict_sentiment`` 호출 (DB 미변경)
    """
    if token not in cache:
        cache[token] = classifier.predict_sentiment(token)
    return cache[token]


def _span_has_opposite_token(
    tokens: list[str],
    candidate: SpanCandidate,
    sentimental: str,
    classifier: BertTokenizer,
    token_cache: dict[str, dict],
) -> bool:
    """span 내 감성형 어절 중 행 sentimental과 반대 label이 뚜렷하면 True.

    Note:
        함수 유형: C+E — 혼합 감성 span 필터
        안전성: Level 1 — 어절별 ``predict_sentiment`` 호출
    """
    for idx in range(candidate.token_start, candidate.token_end):
        token = tokens[idx]
        if not _is_sentiment_shaped_token(token):
            continue
        result = _get_token_sentiment(token, classifier, token_cache)
        if _token_is_opposite_sentiment(result, sentimental):
            return True
    return False


def _is_proper_subspan(inner: SpanCandidate, outer: SpanCandidate) -> bool:
    """inner가 outer의 진부분집합 어절 구간이면 True.

    Note:
        함수 유형: A — 순수 계산
        안전성: Level 0
    """
    if inner.token_start < outer.token_start or inner.token_end > outer.token_end:
        return False
    inner_len = inner.token_end - inner.token_start
    outer_len = outer.token_end - outer.token_start
    return inner_len < outer_len


def _suppress_dominated_spans(
    candidates: list[SpanCandidate],
    eps: float = BertKeywords.SUBSPAN_SCORE_EPS,
) -> list[SpanCandidate]:
    """긴 span 점수가 비슷하면 짧은 subspan 제거 (3어절 우선).

    Note:
        함수 유형: A — 순수 계산
        안전성: Level 0
        불변 규칙: outer.score >= inner.score - eps 이면 inner 제거
    """
    drop: set[int] = set()
    for i, outer in enumerate(candidates):
        if i in drop:
            continue
        for j, inner in enumerate(candidates):
            if i == j or j in drop:
                continue
            if _is_proper_subspan(inner, outer) and outer.score >= inner.score - eps:
                drop.add(j)
    return [c for idx, c in enumerate(candidates) if idx not in drop]


def _spans_overlap(a: SpanCandidate, b: SpanCandidate) -> bool:
    """어절 인덱스 구간 [start, end) 교집합 여부.

    Note:
        함수 유형: A — 순수 계산
        안전성: Level 0
    """
    return not (a.token_end <= b.token_start or b.token_end <= a.token_start)


def _dedupe_best_scores(candidates: list[SpanCandidate]) -> list[SpanCandidate]:
    """동일 span_text는 최고 점수만 유지.

    Note:
        함수 유형: A — 순수 계산
        안전성: Level 0
    """
    best: dict[str, SpanCandidate] = {}
    for cand in candidates:
        prev = best.get(cand.span_text)
        if prev is None or cand.score > prev.score:
            best[cand.span_text] = cand
    return list(best.values())


def _select_non_overlapping_top(
    candidates: list[SpanCandidate],
    top_k: int = BertKeywords.TOP_K,
) -> list[str]:
    """점수 내림차순 greedy — 겹침 제외, 동점 시 긴 span 우선.

    Note:
        함수 유형: A — 순수 계산
        안전성: Level 0
        불변 규칙: 겹치는 span은 상위 1개만 선택, 최대 top_k개
    """
    ranked = sorted(
        candidates,
        key=lambda c: (-c.score, -(c.token_end - c.token_start), c.token_start),
    )
    selected: list[SpanCandidate] = []
    for cand in ranked:
        if any(_spans_overlap(cand, picked) for picked in selected):
            continue
        selected.append(cand)
        if len(selected) == top_k:
            break
    return [c.span_text for c in selected]


def _format_keywords(spans: list[str]) -> str:
    """추출한 키워드를 # 구분자로 묶어 반환.

    Note:
        함수 유형: B — 데이터 변환
        안전성: Level 0
        불변 규칙: 빈 목록이면 빈 문자열
    """
    if not spans:
        return ""
    return "".join(f"#{span}" for span in spans)


def extract_keywords(
    content: str,
    sentimental: str,
    classifier: BertTokenizer,
    *,
    min_window: int = BertKeywords.MIN_WINDOW,
    max_window: int = BertKeywords.MAX_WINDOW,
    top_k: int = BertKeywords.TOP_K,
) -> str:
    """content에서 sentimental 방향에 맞는 BERT 상위 span을 # 구분 keywords 문자열로 반환.

    Args:
        content: 리뷰 본문.
        sentimental: 행 감성 라벨 (``positive`` / ``negative``).
        classifier: ``BertTokenizer`` Singleton 등 감성 추론기.
        min_window: sliding window 최소 어절 수.
        max_window: sliding window 최대 어절 수.
        top_k: 반환할 최대 span 개수.

    Returns:
        ``#span1#span2`` 형식 문자열. 후보 없으면 ``""``.

    Note:
        함수 유형: A+E — span 생성·필터 + BERT 추론
        안전성: Level 1 — ``predict_sentiment`` 다회 호출, DB 미변경
        불변 규칙: label 불일치 span 제외, 혼합 감성 span 제외, 비중복 top_k
    """
    tokens = _preprocessed_tokens(content)
    raw_candidates = _slide_span_candidates(
        tokens, min_window=min_window, max_window=max_window
    )
    if not raw_candidates:
        return ""

    token_cache: dict[str, dict] = {}
    scored: list[SpanCandidate] = []
    for span_text, start, end in raw_candidates:
        if not _is_within_span_chars(span_text):
            continue
        result = classifier.predict_sentiment(span_text)
        score = _span_target_score(result, sentimental)
        if score is None:
            continue
        candidate = SpanCandidate(
            span_text=span_text,
            token_start=start,
            token_end=end,
            score=score,
        )
        if _span_has_opposite_token(tokens, candidate, sentimental, classifier, token_cache):
            continue
        scored.append(candidate)

    if not scored:
        return ""

    filtered = _suppress_dominated_spans(_dedupe_best_scores(scored))
    return _format_keywords(_select_non_overlapping_top(filtered, top_k=top_k))
