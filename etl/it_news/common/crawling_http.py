"""크롤러 공통 HTTP 헤더·URL 순회·CSV 저장."""

from __future__ import annotations

import time
from collections.abc import Callable
from datetime import datetime
from typing import Optional

import pandas as pd
from tqdm import tqdm

from common.constant import CodeTable, CrawlingColumn, CrawlingConstant, Service, Stage, Status
from common.utils import build_csv_path, coalesce_last_created_at, get_run_time, save_csv


def user_agent_headers() -> dict[str, str]:
    """크롤 HTTP 요청용 User-Agent 헤더 dict.

    Note:
        함수 유형: A — 순수 계산
        안전성: Level 0
    """
    return {CrawlingConstant.USER_AGENT_HEADER: CrawlingConstant.USER_AGENT}


def run_crawl_and_save(
    *,
    service: Service,
    article_urls: list[str],
    parse_article: Callable[[str], dict],
    tqdm_desc: str,
    run_time: Optional[datetime] = None,
    last_created_at: Optional[object] = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """게시글 URL 순회·파싱·워터마크 필터 후 raw success/fail CSV 저장.

    Note:
        함수 유형: E+B — 외부 HTTP(콜백) + DataFrame·CSV
        안전성: Level 2 — CSV 쓰기; `parse_article`은 호출부가 E(L3)
        불변 규칙: success는 `created_at > threshold`만 유지
        부작용: `process=raw` CSV; per-URL 예외는 fail 행(`error`)
    """
    if run_time is None:
        run_time = get_run_time()

    threshold = coalesce_last_created_at(last_created_at)
    success_rows: list[dict] = []
    fail_rows: list[dict] = []

    for url in tqdm(article_urls, desc=tqdm_desc, unit="개"):
        try:
            success_rows.append(parse_article(url))
        except Exception as e:
            c = CrawlingColumn
            fail_rows.append({c.ARTICLE_URL.value: url, c.ERROR.value: str(e)})
        time.sleep(CrawlingConstant.REQUEST_DELAY_SECONDS)

    df_success = pd.DataFrame(success_rows)
    df_fail = pd.DataFrame(fail_rows)

    if success_rows:
        t = pd.Timestamp(threshold)
        ca = CrawlingColumn.CREATED_AT.value
        df_success = df_success[df_success[ca] > t].copy()

    info_cd = CodeTable.INFORMATION_IT.value
    svc = service.service

    if not df_success.empty:
        save_csv(
            df_success,
            build_csv_path(Stage.CRAWLING, info_cd, svc, Status.SUCCESS, run_time),
        )

    if not df_fail.empty:
        save_csv(
            df_fail,
            build_csv_path(Stage.CRAWLING, info_cd, svc, Status.FAIL, run_time),
        )

    return df_success, df_fail
