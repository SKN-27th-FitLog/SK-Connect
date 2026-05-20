"""PA-L0-ERR: PostAnalysisErrors 메시지."""

import pytest

from common.errors import PostAnalysisErrors, _missing_columns_message


def test_pa_l0_err_001_missing_columns_message() -> None:
    msg = _missing_columns_message("crawling", "적재", ["title"])
    assert msg == "crawling 데이터에 적재에 필요한 컬럼이 없습니다: title"


def test_pa_l0_err_002_get_reviews_missing_crawling() -> None:
    msg = PostAnalysisErrors.GetReviews.missing_crawling_columns(["a", "b"])
    assert "crawling" in msg and "a, b" in msg


@pytest.mark.parametrize("value", [0, -1])
def test_pa_l0_err_003_invalid_max_rows(value: int) -> None:
    msg = PostAnalysisErrors.Pipeline.invalid_max_rows(value)
    assert "max_rows" in msg and "0보다" in msg


def test_pa_l0_err_004_shop_not_found_warn() -> None:
    assert "shop 미매칭" in PostAnalysisErrors.GetReviews.Warn.shop_not_found(1, None)


def test_pa_l0_err_005_ambiguous_shop_warn() -> None:
    assert "shop_count=3" in PostAnalysisErrors.GetReviews.Warn.ambiguous_shop(1, 100, 3)


def test_pa_l0_err_006_pipeline_step_start() -> None:
    assert PostAnalysisErrors.Pipeline.step_start(1, 3, "get_reviews") == "1/3 get_reviews"
