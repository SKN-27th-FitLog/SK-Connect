import time

from common.logging_config import set_logging
from get_data.get_data import iter_shop_data
from get_data.select_shop import select_keyword, select_shop
from make_post.node import graph
from make_post.to_post import to_post, to_post_vector

logger = set_logging()


def run_pipeline():
    """게시글 생성 후보를 매장 단위로 처리하는 메인 파이프라인."""
    for shop_data in iter_shop_data():
        try:
            keyword_data = []
            keyword_stats = []
            negative_keywords = []
            shop_id = None
            if shop_data:
                shop_id = shop_data[0].get("shop_id")

            # 최소 데이터 수를 만족하지 못하면 LLM 생성 품질이 낮아지므로 건너뛴다.
            if not shop_data:
                logger.info("생성 대상 데이터가 없습니다.")
                continue
            elif len(shop_data) < 5:
                logger.info(f"데이터가 5개 미만입니다. | shop_id={shop_id} | rows={len(shop_data)}")
                continue

            # 긍정 비율 기준을 통과한 매장만 대표 키워드를 추출해 게시글 생성 대상으로 삼는다.
            if not select_shop(shop_data):
                logger.info(f"긍정 비율 조건 미충족 | shop_id={shop_id}")
                continue

            keyword_result = select_keyword(shop_data)
            keyword_data = keyword_result.get("keywords", [])
            keyword_stats = keyword_result.get("keyword_stats", [])
            negative_keywords = keyword_result.get("negative_keywords", [])

            if not keyword_data:
                logger.info(f"생성 키워드 없음 | shop_id={shop_id}")
                continue

            # 게시글 생성 그래프는 생성 -> 제목 생성 -> 유사도 검사 -> 재생성 -> 재검사 -> 평가를 수행한다.
            logger.info(f"graph invoke start | shop_id={shop_id} | rows={len(shop_data)} | keywords={keyword_data}")
            post_data = graph.invoke({
                "keyword": keyword_data,
                "keyword_stats": keyword_stats,
                "negative_keywords": negative_keywords,
                "data": shop_data,
                "post": None,
                "title": None,
                "similar_post": None,
                "reason": None,
                "sample_data": None,
                "source_facts": None,
                "is_pass": None,
                "retry_count": 0,
            })
            logger.info(
                f"graph invoke end | shop_id={shop_id} | "
                f"title_len={len(str(post_data.get('title') or ''))} | "
                f"post_len={len(str(post_data.get('post') or ''))} | "
                f"is_pass={post_data.get('is_pass')} | retry_count={post_data.get('retry_count')}"
            )

            if not post_data or not post_data.get("is_pass"):
                logger.info(f"post evaluation failed after retries, skip save | shop_id={shop_id}")
                continue

            logger.info(f"to_post start | shop_id={shop_id}")
            post_id = to_post(post_data, shop_data[0])
            if post_id is None:
                logger.error(f"게시글 저장 실패 | shop_id={shop_id}")
                continue

            # posts 저장에 성공한 게시글만 벡터 검색용 컬렉션에도 적재한다.
            logger.info(f"to_post success | shop_id={shop_id} | post_id={post_id}")
            logger.info(f"to_post_vector start | shop_id={shop_id} | post_id={post_id}")
            to_post_vector(post_data, shop_data, post_id, keyword_data, keyword_stats)
            logger.info(f"to_post_vector end | shop_id={shop_id} | post_id={post_id}")

        except Exception as e:
            shop_id = None
            if shop_data:
                shop_id = shop_data[0].get("shop_id")
            logger.error(f"Error={e} | shop_id={shop_id} | time={time.time()}")
            continue


if __name__ == "__main__":
    run_pipeline()
