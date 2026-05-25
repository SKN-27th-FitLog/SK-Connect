import time

from common.constants import RESTAURANT_INFORMATION_CD
from common.logging_config import set_logging
from get_data.get_data import get_data
from get_data.select_shop import select_keyword, select_shop
from make_post.node import graph
from make_post.to_post import to_post, to_post_vector

logger = set_logging()

MIN_RESTAURANT_ROWS = 5
SHOP_COOLDOWN_SECONDS = 2.0


def _generation_group_key(row: dict) -> tuple[str, int | str | None]:
    """게시글 생성 단위를 결정한다. 맛집은 shop_id, 그 외는 crawling_id 기준이다."""
    information_cd = row.get("information_cd")
    if information_cd == RESTAURANT_INFORMATION_CD:
        return information_cd, row.get("shop_id")
    return str(information_cd or "UNKNOWN"), row.get("crawling_id")


def _iter_generation_data():
    """get_data 결과를 게시글 생성 단위별로 묶어서 반환한다."""
    groups = {}
    group_order = []

    for row in get_data() or []:
        key = _generation_group_key(row)
        if key[1] is None:
            logger.info(f"생성 기준값 없음, skip | information_cd={row.get('information_cd')}")
            continue

        if key not in groups:
            groups[key] = []
            group_order.append(key)
        groups[key].append(row)

    for key in group_order:
        yield groups[key]


def _should_skip_group(group_data: list[dict]) -> bool:
    """생성 전 최소 조건을 확인한다."""
    if not group_data:
        logger.info("생성 대상 데이터가 없습니다.")
        return True

    first_row = group_data[0]
    information_cd = first_row.get("information_cd")
    shop_id = first_row.get("shop_id")
    crawling_id = first_row.get("crawling_id")

    if information_cd == RESTAURANT_INFORMATION_CD and len(group_data) < MIN_RESTAURANT_ROWS:
        logger.info(f"맛집 데이터가 5개 미만입니다. | shop_id={shop_id} | rows={len(group_data)}")
        return True

    if not select_shop(group_data):
        logger.info(
            f"긍정 비율 조건 미충족 | information_cd={information_cd} | "
            f"shop_id={shop_id} | crawling_id={crawling_id}"
        )
        return True

    return False


def run_pipeline():
    """게시글 생성 후보를 생성 단위별로 처리하는 메인 파이프라인."""
    for group_data in _iter_generation_data():
        first_row = group_data[0] if group_data else {}
        information_cd = first_row.get("information_cd")
        shop_id = first_row.get("shop_id")
        crawling_id = first_row.get("crawling_id")

        try:
            if _should_skip_group(group_data):
                continue

            keyword_result = select_keyword(group_data)
            keyword_data = keyword_result.get("keywords", [])
            keyword_stats = keyword_result.get("keyword_stats", [])
            negative_keywords = keyword_result.get("negative_keywords", [])

            if not keyword_data:
                logger.info(
                    f"생성 키워드 없음 | information_cd={information_cd} | "
                    f"shop_id={shop_id} | crawling_id={crawling_id}"
                )
                continue

            logger.info(
                f"graph invoke start | information_cd={information_cd} | "
                f"shop_id={shop_id} | crawling_id={crawling_id} | "
                f"rows={len(group_data)} | keywords={keyword_data}"
            )
            post_data = graph.invoke({
                "keyword": keyword_data,
                "keyword_stats": keyword_stats,
                "negative_keywords": negative_keywords,
                "data": group_data,
                "post": None,
                "title": None,
                "reason": None,
                "sample_data": None,
                "image_list": None,
                "source_facts": None,
                "is_pass": None,
                "retry_count": 0,
            })
            logger.info(
                f"graph invoke end | shop_id={shop_id} | crawling_id={crawling_id} | "
                f"title_len={len(str(post_data.get('title') or ''))} | "
                f"post_len={len(str(post_data.get('post') or ''))} | "
                f"is_pass={post_data.get('is_pass')} | retry_count={post_data.get('retry_count')}"
            )
            time.sleep(SHOP_COOLDOWN_SECONDS)

            if not post_data or not post_data.get("is_pass"):
                logger.info(f"post evaluation failed after retries, skip save | shop_id={shop_id} | crawling_id={crawling_id}")
                continue

            logger.info(f"to_post start | shop_id={shop_id} | crawling_id={crawling_id}")
            post_id = to_post(post_data, first_row)
            if post_id is None:
                logger.error(f"게시글 저장 실패 | shop_id={shop_id} | crawling_id={crawling_id}")
                continue

            logger.info(f"to_post success | shop_id={shop_id} | crawling_id={crawling_id} | post_id={post_id}")
            logger.info(f"to_post_vector start | shop_id={shop_id} | crawling_id={crawling_id} | post_id={post_id}")
            to_post_vector(post_data, group_data, post_id, keyword_data, keyword_stats)
            logger.info(f"to_post_vector end | shop_id={shop_id} | crawling_id={crawling_id} | post_id={post_id}")

        except Exception as e:
            logger.error(
                f"run_pipeline group error | Error={e} | information_cd={information_cd} | "
                f"shop_id={shop_id} | crawling_id={crawling_id} | time={time.time()}"
            )
            continue


if __name__ == "__main__":
    run_pipeline()
