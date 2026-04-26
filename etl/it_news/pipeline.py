"""ETL 전체 오케스트레이터: 크롤링(geeknews → pytorch) → 클리닝 → save(DB 적재, CSV)."""
from __future__ import annotations

import logging

from cleaning.cleaning import cleaning_threads
from common.utils import get_last_success_date_by_thread_prefix, get_run_time
from crawling.crawling_thread_geeknews import crawling_thread_geeknews
from crawling.crawling_thread_pytorch import crawling_thread_pytorch
from save.save import save_threads

logger = logging.getLogger(__name__)


def run_pipeline() -> None:
    """한 프로세스에서 1) 두 소스 크롤, 2) 클리닝, 3) 저장 순으로 실행."""
    # 같은 `run_time`으로 두 크롤 출력이 동일 run 폴더에 쌓이도록
    run_time = get_run_time()
    last_geek = get_last_success_date_by_thread_prefix("geeknews_")
    last_pt = get_last_success_date_by_thread_prefix("pytorch_")

    logger.info("1/4 크롤링 geeknews")
    g_ok, g_fail = crawling_thread_geeknews(
        run_time=run_time, last_created_at=last_geek
    )
    logger.info("   geeknews: success=%d fail=%d", len(g_ok), len(g_fail))

    logger.info("2/4 크롤링 pytorch")
    p_ok, p_fail = crawling_thread_pytorch(
        run_time=run_time, last_created_at=last_pt
    )
    logger.info("   pytorch: success=%d fail=%d", len(p_ok), len(p_fail))

    logger.info("3/4 클리닝")
    c_ok, c_fail = cleaning_threads()
    logger.info("   cleaning: success=%d fail=%d", len(c_ok), len(c_fail))

    logger.info("4/4 save(DB + CSV)")
    s_ok, s_fail = save_threads()
    logger.info("   save: success=%d fail=%d", len(s_ok), len(s_fail))

    logger.info("파이프라인 종료.")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s [%(name)s] %(message)s",
    )
    run_pipeline()
