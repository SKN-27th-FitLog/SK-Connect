"""PA-L0-ERR: PostAnalysisErrors 메시지 (Level 0, DB 미접촉)."""

import pytest

from common.errors import PostAnalysisErrors, _missing_columns_message


def test_pa_l0_err_001_missing_columns_message() -> None:
    """PA-L0-ERR-001 [정상]: _missing_columns_message 포맷 문자열."""
    msg = _missing_columns_message("crawling", "적재", ["title"])
    assert msg == "crawling 데이터에 적재에 필요한 컬럼이 없습니다: title"


def test_pa_l0_err_002_get_reviews_missing_crawling() -> None:
    """PA-L0-ERR-002 [정상]: GetReviews.missing_crawling_columns 래퍼."""
    msg = PostAnalysisErrors.GetReviews.missing_crawling_columns(["a", "b"])
    assert "crawling" in msg and "a, b" in msg


@pytest.mark.parametrize("value", [0, -1])
def test_pa_l0_err_003_invalid_max_rows(value: int) -> None:
    """PA-L0-ERR-003 [정상]: max_rows 0 이하일 때 ValueError 메시지."""
    msg = PostAnalysisErrors.Pipeline.invalid_max_rows(value)
    assert "max_rows" in msg and "0보다" in msg


def test_pa_l0_err_004_shop_not_found_warn() -> None:
    """PA-L0-ERR-004 [정상]: shop 미매칭 warning 문구."""
    assert "shop 미매칭" in PostAnalysisErrors.GetReviews.Warn.shop_not_found(1, None)


def test_pa_l0_err_005_ambiguous_shop_warn() -> None:
    """PA-L0-ERR-005 [정상]: shop N:1 ambiguous warning 문구."""
    assert "shop_count=3" in PostAnalysisErrors.GetReviews.Warn.ambiguous_shop(1, 100, 3)


def test_pa_l0_err_006_pipeline_step_start() -> None:
    """PA-L0-ERR-006 [정상]: 파이프라인 단계 시작 로그 포맷."""
    assert PostAnalysisErrors.Pipeline.step_start(1, 3, "get_reviews") == "1/3 get_reviews"
