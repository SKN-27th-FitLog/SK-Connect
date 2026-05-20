"""PA-L2-GRV: get_reviews 간접 검증 (merge·get_* patch)."""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from common.constant import AnalysisColumn, CodeTable, CrawlingColumn, ShopColumn
from get_reviews import get_reviews


def _crawl_df(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(rows)


def _shop_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            ShopColumn.MAP_ID.value: [100],
            ShopColumn.SHOP_ID.value: [1],
            ShopColumn.SHOP_CD.value: ["S01"],
        }
    )


@patch("get_reviews.merge_analysis_data")
@patch("get_reviews.get_shop_data")
@patch("get_reviews.get_analysis_data")
@patch("get_reviews.get_crawling_data")
def test_pa_l2_grv_001_missing_crawling_column(
    mock_crawl: MagicMock,
    mock_an: MagicMock,
    mock_shop: MagicMock,
    mock_merge: MagicMock,
) -> None:
    mock_crawl.return_value = pd.DataFrame({"x": [1]})
    mock_an.return_value = pd.DataFrame({AnalysisColumn.CRAWLING_ID.value: []})
    mock_shop.return_value = _shop_df()

    with pytest.raises(ValueError, match="crawling"):
        get_reviews()
    mock_merge.assert_not_called()


@patch("get_reviews.merge_analysis_data")
@patch("get_reviews.get_shop_data")
@patch("get_reviews.get_analysis_data")
@patch("get_reviews.get_crawling_data")
def test_pa_l2_grv_004_ic01_and_excludes_ca07(
    mock_crawl: MagicMock,
    mock_an: MagicMock,
    mock_shop: MagicMock,
    mock_merge: MagicMock,
) -> None:
    cid = CrawlingColumn.CRAWLING_ID.value
    mock_crawl.return_value = _crawl_df(
        [
            {
                cid: -900000010,
                CrawlingColumn.TITLE.value: "t",
                CrawlingColumn.CONTENT.value: "c",
                CrawlingColumn.ARTICLE_URL.value: "u",
                CrawlingColumn.MAP_ID.value: 100,
                CrawlingColumn.CATEGORY_CD.value: "CA01",
            },
            {
                cid: -900000011,
                CrawlingColumn.TITLE.value: "it",
                CrawlingColumn.CONTENT.value: "c",
                CrawlingColumn.ARTICLE_URL.value: "u",
                CrawlingColumn.MAP_ID.value: 100,
                CrawlingColumn.CATEGORY_CD.value: CodeTable.CATEGORY_ETC.value,
            },
        ]
    )
    mock_an.return_value = pd.DataFrame({AnalysisColumn.CRAWLING_ID.value: []})
    mock_shop.return_value = _shop_df()

    get_reviews()

    mock_merge.assert_called_once()
    df = mock_merge.call_args[0][0]
    assert len(df) == 1
    assert (df[AnalysisColumn.INFORMATION_CD.value] == CodeTable.INFORMATION_RESTAURANT.value).all()


@patch("get_reviews.merge_analysis_data")
@patch("get_reviews.get_shop_data")
@patch("get_reviews.get_analysis_data")
@patch("get_reviews.get_crawling_data")
def test_pa_l2_grv_005_skips_existing_crawling_id(
    mock_crawl: MagicMock,
    mock_an: MagicMock,
    mock_shop: MagicMock,
    mock_merge: MagicMock,
) -> None:
    cid = CrawlingColumn.CRAWLING_ID.value
    existing = -900000020
    mock_crawl.return_value = _crawl_df(
        [
            {
                cid: existing,
                CrawlingColumn.TITLE.value: "t",
                CrawlingColumn.CONTENT.value: "c",
                CrawlingColumn.ARTICLE_URL.value: "u",
                CrawlingColumn.MAP_ID.value: 100,
                CrawlingColumn.CATEGORY_CD.value: "CA01",
            },
        ]
    )
    mock_an.return_value = pd.DataFrame({AnalysisColumn.CRAWLING_ID.value: [existing]})
    mock_shop.return_value = _shop_df()

    get_reviews()
    mock_merge.assert_not_called()
