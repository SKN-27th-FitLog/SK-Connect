"""PA-L0-SHP: _filter_rows_by_shop_match."""

import pandas as pd
import pytest

from common.constant import CrawlingColumn, ShopColumn
from get_reviews import _filter_rows_by_shop_match


def _shop_1to1() -> pd.DataFrame:
    return pd.DataFrame(
        {
            ShopColumn.MAP_ID.value: [100],
            ShopColumn.SHOP_ID.value: [1],
            ShopColumn.SHOP_CD.value: ["S01"],
        }
    )


def _shop_ambiguous() -> pd.DataFrame:
    return pd.DataFrame(
        {
            ShopColumn.MAP_ID.value: [200, 200],
            ShopColumn.SHOP_ID.value: [2, 3],
            ShopColumn.SHOP_CD.value: ["S02", "S03"],
        }
    )


def _crawl_row(crawling_id: int, map_id) -> pd.DataFrame:  # noqa: ANN001
    return pd.DataFrame(
        {
            CrawlingColumn.CRAWLING_ID.value: [crawling_id],
            CrawlingColumn.MAP_ID.value: [map_id],
            CrawlingColumn.TITLE.value: ["t"],
        }
    )


def test_pa_l0_shp_001_empty_crawling() -> None:
    out = _filter_rows_by_shop_match(
        pd.DataFrame(),
        _shop_1to1(),
        crawling_id_col=CrawlingColumn.CRAWLING_ID.value,
        map_id_col=CrawlingColumn.MAP_ID.value,
    )
    assert out.empty


def test_pa_l0_shp_002_one_to_one_match() -> None:
    out = _filter_rows_by_shop_match(
        _crawl_row(1, 100),
        _shop_1to1(),
        crawling_id_col=CrawlingColumn.CRAWLING_ID.value,
        map_id_col=CrawlingColumn.MAP_ID.value,
    )
    assert len(out) == 1
    assert out[ShopColumn.SHOP_ID.value].iloc[0] == 1
    assert out[ShopColumn.SHOP_CD.value].iloc[0] == "S01"


def test_pa_l0_shp_003_null_map_id_dropped() -> None:
    out = _filter_rows_by_shop_match(
        _crawl_row(2, None),
        _shop_1to1(),
        crawling_id_col=CrawlingColumn.CRAWLING_ID.value,
        map_id_col=CrawlingColumn.MAP_ID.value,
    )
    assert out.empty


def test_pa_l0_shp_004_unknown_map_id_dropped() -> None:
    out = _filter_rows_by_shop_match(
        _crawl_row(3, 999),
        _shop_1to1(),
        crawling_id_col=CrawlingColumn.CRAWLING_ID.value,
        map_id_col=CrawlingColumn.MAP_ID.value,
    )
    assert out.empty


def test_pa_l0_shp_005_ambiguous_shop_dropped() -> None:
    out = _filter_rows_by_shop_match(
        _crawl_row(4, 200),
        _shop_ambiguous(),
        crawling_id_col=CrawlingColumn.CRAWLING_ID.value,
        map_id_col=CrawlingColumn.MAP_ID.value,
    )
    assert out.empty


def test_pa_l0_shp_006_string_map_id_normalized() -> None:
    out = _filter_rows_by_shop_match(
        _crawl_row(5, "100"),
        _shop_1to1(),
        crawling_id_col=CrawlingColumn.CRAWLING_ID.value,
        map_id_col=CrawlingColumn.MAP_ID.value,
    )
    assert len(out) == 1


def test_pa_l0_shp_007_warns_on_null_map_id(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level("WARNING"):
        _filter_rows_by_shop_match(
            _crawl_row(2, None),
            _shop_1to1(),
            crawling_id_col=CrawlingColumn.CRAWLING_ID.value,
            map_id_col=CrawlingColumn.MAP_ID.value,
        )
    assert any("shop 미매칭" in r.message for r in caplog.records)
