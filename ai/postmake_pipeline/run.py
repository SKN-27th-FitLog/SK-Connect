from extract_keyword.from_crawling import GetCrawlingData
from extract_keyword.data_pre import DataPreprocessing
from common.logging_config import set_logging
from common.prompt import Create_Prompt
logger = set_logging()


def run_pipeline():
    get_data = GetCrawlingData()
    data_pre = DataPreprocessing()
    prompt = Create_Prompt()
    
    while True:
        try:
            ###############################
            # 1. 키워드 추출 + shop 선정
            ###############################
            data:list[dict] = get_data.get_crawling_data() # crawling 테이블에서 데이터를 가져옴
            if not data:
                logger.info("데이터가 없습니다.")
                break
            data = data_pre.execute(data) # 데이터 전처리

            ###############################
            # 2. 게시글 생성
            ###############################


        except Exception as e:
            logger.error(f"Error={e}")
            break


if __name__ == "__main__":
    run_pipeline()

