"""PA-L0-BKW: common/bert_keywords 순수 헬퍼 (Level 0, BERT·DB 미접촉)."""

from unittest.mock import MagicMock

from common.bert_keywords import (
    SpanCandidate,
    _format_keywords,
    _is_proper_subspan,
    _preprocess_content,
    _preprocessed_tokens,
    _select_non_overlapping_top,
    _slide_span_candidates,
    _span_target_score,
    _spans_overlap,
    _suppress_dominated_spans,
    extract_keywords,
)
from common.constant import SentimentLabel, SentimentResultKey


def test_pa_l0_bkw_001_format_keywords_empty() -> None:
    """PA-L0-BKW-001 [경계]: 빈 span 목록이면 빈 문자열."""
    assert _format_keywords([]) == ""


def test_pa_l0_bkw_002_format_keywords_join() -> None:
    """PA-L0-BKW-002 [정상]: span을 # 접두로 연결."""
    assert _format_keywords(["맛있어요", "가성비 좋아요"]) == "#맛있어요#가성비 좋아요"


def test_pa_l0_bkw_003_preprocess_content() -> None:
    """PA-L0-BKW-003 [정상]: 마침표·특수문자 제거 후 공백 정규화."""
    assert _preprocess_content("맛있어요!!! 가격도.") == "맛있어요 가격도"


def test_pa_l0_bkw_004_preprocessed_tokens_excludes_jamo() -> None:
    """PA-L0-BKW-004 [불변]: 자음·모음 단독 어절(ㅠ) 제외."""
    tokens = _preprocessed_tokens("맛있어요 ㅠ 또 방문")
    assert "ㅠ" not in tokens
    assert tokens == ["맛있어요", "또", "방문"]


def test_pa_l0_bkw_005_slide_span_candidates() -> None:
    """PA-L0-BKW-005 [정상]: 3어절 입력에서 2·3어절 window 후보 생성."""
    tokens = ["a", "b", "c"]
    candidates = _slide_span_candidates(tokens, min_window=2, max_window=3)
    texts = [c[0] for c in candidates]
    assert "a b" in texts
    assert "b c" in texts
    assert "a b c" in texts


def test_pa_l0_bkw_006_span_target_score_mismatch() -> None:
    """PA-L0-BKW-006 [불변]: BERT label과 행 sentimental 불일치 시 None."""
    result = {
        SentimentResultKey.SENTIMENTAL.value: SentimentLabel.NEGATIVE.value,
        SentimentResultKey.POSITIVE_SCORE.value: 0.2,
        SentimentResultKey.NEGATIVE_SCORE.value: 0.8,
    }
    assert _span_target_score(result, SentimentLabel.POSITIVE.value) is None


def test_pa_l0_bkw_007_span_target_score_match() -> None:
    """PA-L0-BKW-007 [정상]: label 일치 시 해당 방향 score 반환."""
    result = {
        SentimentResultKey.SENTIMENTAL.value: SentimentLabel.POSITIVE.value,
        SentimentResultKey.POSITIVE_SCORE.value: 0.91,
        SentimentResultKey.NEGATIVE_SCORE.value: 0.09,
    }
    assert _span_target_score(result, SentimentLabel.POSITIVE.value) == 0.91


def test_pa_l0_bkw_008_spans_overlap() -> None:
    """PA-L0-BKW-008 [불변]: 어절 구간 교집합 판별."""
    a = SpanCandidate("a b", 0, 2, 0.9)
    b = SpanCandidate("b c", 1, 3, 0.8)
    c = SpanCandidate("d e", 3, 5, 0.7)
    assert _spans_overlap(a, b) is True
    assert _spans_overlap(a, c) is False


def test_pa_l0_bkw_009_suppress_dominated_spans() -> None:
    """PA-L0-BKW-009 [불변]: 긴 span이 우세하면 짧은 subspan 제거."""
    outer = SpanCandidate("a b c", 0, 3, 0.9)
    inner = SpanCandidate("a b", 0, 2, 0.88)
    kept = _suppress_dominated_spans([outer, inner], eps=0.05)
    assert len(kept) == 1
    assert kept[0].span_text == "a b c"


def test_pa_l0_bkw_010_select_non_overlapping_top() -> None:
    """PA-L0-BKW-010 [불변]: 겹치는 span은 점수 상위 1개만, top_k=2."""
    c1 = SpanCandidate("a b", 0, 2, 0.95)
    c2 = SpanCandidate("b c", 1, 3, 0.9)
    c3 = SpanCandidate("x y", 4, 6, 0.85)
    selected = _select_non_overlapping_top([c1, c2, c3], top_k=2)
    assert selected == ["a b", "x y"]


def test_pa_l0_bkw_011_is_proper_subspan() -> None:
    """PA-L0-BKW-011 [불변]: 진부분집합 어절 구간만 subspan."""
    inner = SpanCandidate("a b", 0, 2, 0.5)
    outer = SpanCandidate("a b c", 0, 3, 0.6)
    same = SpanCandidate("a b c", 0, 3, 0.4)
    assert _is_proper_subspan(inner, outer) is True
    assert _is_proper_subspan(outer, same) is False


def test_pa_l0_bkw_012_extract_keywords_empty_skips_bert() -> None:
    """PA-L0-BKW-012 [경계]: 빈 content면 BERT 미호출·빈 문자열."""
    classifier = MagicMock()
    assert extract_keywords("", SentimentLabel.POSITIVE.value, classifier) == ""
    classifier.predict_sentiment.assert_not_called()
