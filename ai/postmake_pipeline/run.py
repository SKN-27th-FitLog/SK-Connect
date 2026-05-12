import time

from common.logging_config import set_logging
from get_data.get_data import iter_shop_data
from get_data.select_shop import select_keyword, select_shop
from make_post.node import graph
from make_post.to_post import to_post, to_post_vector

logger = set_logging()


def run_pipeline():
    for shop_data in iter_shop_data():
        try:
            keyword_data = []
            shop_id = shop_data[0].get("shop_id") if shop_data else None
            if not shop_data:
                logger.info("생성 대상 데이터가 없습니다.")
                continue
            elif len(shop_data) < 5:
                logger.info(f"데이터가 5개 미만입니다. | shop_id={shop_id} | rows={len(shop_data)}")
                continue

            if select_shop(shop_data):
                keyword_data = select_keyword(shop_data)
            else:
                logger.info(f"긍정 비율 조건 미충족 | shop_id={shop_id}")
                continue

            logger.info(f"graph invoke start | shop_id={shop_id} | rows={len(shop_data)} | keywords={keyword_data}")
            post_data = graph.invoke({
                "keyword": keyword_data,
                "data": shop_data,
                "post": None,
                "title": None,
                "similar_post": None,
                "reason": None,
                "sample_data": None,
                "is_pass": None,
                "retry_count": 0,
            })
            logger.info(
                f"graph invoke end | shop_id={shop_id} | "
                f"title_len={len(str(post_data.get('title') or ''))} | "
                f"post_len={len(str(post_data.get('post') or ''))} | "
                f"is_pass={post_data.get('is_pass')} | retry_count={post_data.get('retry_count')}"
            )

            logger.info(f"to_post start | shop_id={shop_id}")
            post_id = to_post(post_data, shop_data[0])
            if post_id is None:
                logger.error(f"게시글 저장 실패 | shop_id={shop_id}")
                continue

            logger.info(f"to_post success | shop_id={shop_id} | post_id={post_id}")
            logger.info(f"to_post_vector start | shop_id={shop_id} | post_id={post_id}")
            to_post_vector(post_data, shop_data, post_id, keyword_data)
            logger.info(f"to_post_vector end | shop_id={shop_id} | post_id={post_id}")

        except Exception as e:
            shop_id = shop_data[0].get("shop_id") if shop_data else None
            logger.error(f"Error={e} | shop_id={shop_id} | time={time.time()}")
            continue


if __name__ == "__main__":
    run_pipeline()
