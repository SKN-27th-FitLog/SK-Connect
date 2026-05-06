from get_data.get_data import get_shop_data
from get_data.select_shop import select_shop, select_keyword
from common.logging_config import set_logging
from make_post.node import graph
from make_post.to_post import to_post, to_post_vector
import time
logger = set_logging()


def run_pipeline():

    while True:
        try:
            keyword_data = []
            #################Load Data#####################
            shop_data = get_shop_data()
            if not shop_data:
                logger.info("데이터가 없습니다.")
                break
            elif len(shop_data) < 5:
                logger.info("데이터가 5개 미만입니다.")
                break
            #################Select Shop#####################
            if select_shop(shop_data): # 해당 음식점 선택
                keyword_data = select_keyword(shop_data).keys()
            else: # 해당 음식점 선택 실패
                continue # 다음 음식점 확인
            ###################make post####################
            post_data = graph.invoke(keyword_data, shop_data)
            post_id = to_post(post_data, shop_data[0])
            to_post_vector(post_data, shop_data[0],post_id, keyword_data)

        except Exception as e:
            logger.error(f"Error={e} | time={time.time()}")
            break


if __name__ == "__main__":
    run_pipeline()

