"""`crawling`에만 있는 신규 행을 `analysis` 스키마로 옮겨 적재한다."""

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 패키지
import pandas as pd
from datetime import datetime

# 모듈
from common.constant import (
    AnalysisColumn,
    CodeTable,
    CrawlingColumn,
    GetReviewsConfig,
    ShopColumn,
)
from common.errors import PostAnalysisErrors
from postgresql.run_query import (
    get_analysis_data,
    get_crawling_data,
    get_shop_data,
    merge_analysis_data,
)


def _filter_rows_by_shop_match(
    df_crawling: pd.DataFrame,
    df_shop: pd.DataFrame,
    *,
    crawling_id_col: str,
    map_id_col: str,
) -> pd.DataFrame:
    """``shop.map_id`` 기준 1:1 매칭되는 행만 남긴다.

    - ``map_id`` 결측·shop 0건 → ``GetReviews.Warn.shop_not_found`` 후 드랍
    - shop 2건 이상 → ``GetReviews.Warn.ambiguous_shop`` 후 드랍
    - 1:1만 통과 (``shop_id``, ``shop_cd``는 호출 측에서 merge)

    Args:
        df_crawling: shop 매칭 대상 crawling 행.
        df_shop: shop 마스터.
        crawling_id_col: crawling 쪽 식별 컬럼명.
        map_id_col: crawling 쪽 ``map_id`` 컬럼명.

    Returns:
        ``shop_id``·``shop_cd``가 붙은 1:1 매칭 행만 남긴 DataFrame.
        매칭 실패 행은 제외(``logger.warning``).

    Note:
        함수 유형: A+B+C — 순수 변환 + shop 유효성 검증
        안전성: Level 0 — DB 미접근 (입력 DataFrame만 변환)
        부작용: ``logger.warning`` (매칭 실패 행)
    """
    if df_crawling.empty:
        return df_crawling

    shop_map_col = ShopColumn.MAP_ID.value

    #################################################
    # shop · crawling map_id 타입 정규화 (merge 키 일치)
    #################################################
    df_shop = df_shop.copy()
    df_shop[shop_map_col] = pd.to_numeric(df_shop[shop_map_col], errors="coerce")

    warn = PostAnalysisErrors.GetReviews.Warn

    #################################################
    # map_id 결측 행 — shop 조회 불가 → warning 후 제외
    #################################################
    null_mask = df_crawling[map_id_col].isna()
    for _, row in df_crawling[null_mask].iterrows():
        logger.warning(warn.shop_not_found(row[crawling_id_col], row[map_id_col]))

    df_work = df_crawling[~null_mask].copy()
    if df_work.empty:
        return df_work

    df_work[map_id_col] = pd.to_numeric(df_work[map_id_col], errors="coerce")

    #################################################
    # map_id별 shop 건수 집계 → 1:1만 통과 (0건·N건은 드랍)
    #################################################
    shop_counts = df_shop.groupby(shop_map_col, dropna=False).size()

    merged = df_work.merge(
        shop_counts.reset_index(name="_shop_n"),
        left_on=map_id_col,
        right_on=shop_map_col,
        how="left",
    )
    merged["_shop_n"] = merged["_shop_n"].fillna(0).astype(int)

    # shop 0건 (map_id에 해당 가게 없음)
    for _, row in merged[merged["_shop_n"] == 0].iterrows():
        logger.warning(
            warn.shop_not_found(row[crawling_id_col], row[map_id_col])
        )

    # shop 2건 이상 — 현재는 1:1 가정, 선택 기준 확정 시 후속 작업
    for _, row in merged[merged["_shop_n"] > 1].iterrows():
        logger.warning(
            warn.ambiguous_shop(
                row[crawling_id_col], row[map_id_col], int(row["_shop_n"])
            )
        )

    ok = merged[merged["_shop_n"] == 1].copy()

    #################################################
    # 1:1 map_id에 shop_id · shop_cd 부여
    #################################################
    one_to_one_maps = shop_counts[shop_counts == 1].index
    shop_lookup = df_shop[df_shop[shop_map_col].isin(one_to_one_maps)][
        [shop_map_col, ShopColumn.SHOP_ID.value, ShopColumn.SHOP_CD.value]
    ].drop_duplicates(subset=[shop_map_col])

    ok = ok.merge(
        shop_lookup,
        left_on=map_id_col,
        right_on=shop_map_col,
        how="left",
        suffixes=("", "_shop"),
    )
    if shop_map_col + "_shop" in ok.columns:
        ok = ok.drop(columns=[shop_map_col + "_shop"])

    # crawling 원본 컬럼 + shop 조회 결과만 반환
    crawl_cols = [c for c in df_crawling.columns if c in ok.columns]
    extra = [ShopColumn.SHOP_ID.value, ShopColumn.SHOP_CD.value]
    return ok[crawl_cols + [c for c in extra if c in ok.columns]]


def get_reviews() -> None:
    """``crawling`` 신규 행을 ``analysis`` 스키마로 변환해 MERGE 적재한다.

    처리 순서:
        1. ``crawling`` / ``analysis`` / ``shop`` 조회
        2. 이미 ``analysis``에 있는 ``crawling_id`` 제외
        3. ``category_cd=CA07``(IT) → shop 매칭 생략, ``information_cd=IC02``
        4. 그 외 → ``_filter_rows_by_shop_match``로 shop 1:1 매칭, ``information_cd=IC01``
        5. analysis 컬럼 매핑, ``created_dt=now``
        6. ``merge_analysis_data`` UPSERT

    Raises:
        ValueError: 필수 crawling/analysis 컬럼 누락.

    Note:
        함수 유형: B+D+F — 변환 + DB 조회·저장 + 배치 오케스트레이션
        안전성: Level 2 — ``analysis`` UPSERT (autocommit)
        불변 규칙: 신규 ``crawling_id``만 insert, CA07→IC02(적재만), 그 외→IC01
    """
    ###################################################
    # 데이터 설정
    ###################################################

    cid_crawl = CrawlingColumn.CRAWLING_ID.value
    cid_an = AnalysisColumn.CRAWLING_ID.value
    title_c, title_a = CrawlingColumn.TITLE.value, AnalysisColumn.TITLE.value
    content_c, content_a = CrawlingColumn.CONTENT.value, AnalysisColumn.CONTENT.value
    url_c, url_a = CrawlingColumn.ARTICLE_URL.value, AnalysisColumn.ARTICLE_URL.value
    map_c, map_a = CrawlingColumn.MAP_ID.value, AnalysisColumn.MAP_ID.value
    shop_a = AnalysisColumn.SHOP_ID.value
    shop_cd_a = AnalysisColumn.SHOP_CD.value
    cat_c, cat_a = CrawlingColumn.CATEGORY_CD.value, AnalysisColumn.CATEGORY_CD.value
    info_a = AnalysisColumn.INFORMATION_CD.value
    created_a = AnalysisColumn.CREATED_DT.value
    shop_id_col = ShopColumn.SHOP_ID.value
    shop_cd_col = ShopColumn.SHOP_CD.value

    # 현재 시간 가져오기
    now = datetime.now().isoformat(timespec=GetReviewsConfig.ISOFORMAT_TIMESPEC)

    # 테이블 데이터 가져오기
    df_crawling = get_crawling_data()
    df_analysis = get_analysis_data()
    df_shop = get_shop_data()

    crawl_required = (
        cid_crawl,
        title_c,
        content_c,
        url_c,
        map_c,
        cat_c,
    )
    missing_crawl = [c for c in crawl_required if c not in df_crawling.columns]
    if missing_crawl:
        raise ValueError(
            PostAnalysisErrors.GetReviews.missing_crawling_columns(missing_crawl)
        )

    if cid_an not in df_analysis.columns:
        raise ValueError(
            PostAnalysisErrors.GetReviews.missing_analysis_columns([cid_an])
        )

    # => df_analysis에서 crawling_id 컬럼값만 남김
    df_analysis_created = df_analysis[[cid_an]]

    #################################################
    # 데이터 처리
    #################################################

    # df_crawling에서 df_analysis_created 값과 같은 crawling_id가 있으면 드랍 (불리언 인덱싱)
    df_crawling_drop = df_crawling[~df_crawling[cid_crawl].isin(df_analysis_created[cid_an])]

    # 기존에는 음식점 리뷰만 처리하도록 했는데 이제는 모든 카테고리에서 리뷰를 처리하도록 수정 
    # 수정 시 음식점 리뷰와 IT 리뷰를 분리하여 처리하도록 함 
    it_mask = df_crawling_drop[cat_c] == CodeTable.CATEGORY_ETC.value
    df_it = df_crawling_drop[it_mask].copy()
    df_shop_target = df_crawling_drop[~it_mask]

    df_shop_matched = _filter_rows_by_shop_match(
        df_shop_target,
        df_shop,
        crawling_id_col=cid_crawl,
        map_id_col=map_c,
    )

    if not df_it.empty:
        df_it[shop_id_col] = pd.NA
        df_it[shop_cd_col] = pd.NA

    parts = [df for df in (df_shop_matched, df_it) if not df.empty]
    df_crawling_drop = (
        pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()
    )

    if df_crawling_drop.empty:
        logger.info(PostAnalysisErrors.GetReviews.no_rows_after_shop_resolve())
        return

    # df_crawling_drop 데이터를 analysis 테이블에 맞게 재설정 (컬럼별로 추가)
    df_analysis_new = pd.DataFrame()
    df_analysis_new[cid_an] = df_crawling_drop[cid_crawl]
    df_analysis_new[title_a] = df_crawling_drop[title_c]
    df_analysis_new[content_a] = df_crawling_drop[content_c]
    df_analysis_new[url_a] = df_crawling_drop[url_c]
    df_analysis_new[map_a] = df_crawling_drop[map_c]
    df_analysis_new[shop_a] = df_crawling_drop[shop_id_col]
    df_analysis_new[shop_cd_a] = df_crawling_drop[shop_cd_col]
    df_analysis_new[cat_a] = df_crawling_drop[cat_c]
    info_by_category = {
        CodeTable.CATEGORY_ETC.value: CodeTable.INFORMATION_IT_INFO.value,
    }
    df_analysis_new[info_a] = (
        df_crawling_drop[cat_c]
        .map(info_by_category)
        .fillna(CodeTable.INFORMATION_RESTAURANT.value)
    )
    df_analysis_new[created_a] = now

    #################################################
    # 처리된 데이터를 analysis 테이블에 업데이트
    #################################################
    merge_analysis_data(df_analysis_new)
    logger.info("데이터 적용 완료 (%s건)", len(df_analysis_new))


if __name__ == "__main__":
    get_reviews()
