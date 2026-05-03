from get_data.get_data import get_shop_data
from get_data.select_shop import select_shop, select_keyword
from common.logging_config import set_logging
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
                keyword_data = select_keyword(shop_data)
            else: # 해당 음식점 선택 실패
                continue # 다음 음식점 확인
            #######################################

        except Exception as e:
            logger.error(f"Error={e} | time={time.time()}")
            break


if __name__ == "__main__":
    run_pipeline()

