from src.from_crawling import GetCrawlingData
from src.data_pre import DataPreprocessing
from src.logging_config import set_logging
from src.prompt import Prompt
from src.to_post import to_post, to_post_vector
from src.node import graph
logger = set_logging()


def run_pipeline():
    batch_count = 0
    attempted_crawling_ids: set[int] = set()
    crawling = GetCrawlingData()
    data_pre = DataPreprocessing()
    graph_compile = graph()

    while True:
        data:list[dict] = crawling.route_crawling_data() #crawling한 데이터를 가져옴
        if not data:
            logger.info("데이터가 없습니다.")
            break #데이터가 없으면 종료

        # 이번 실행에서 이미 시도한 데이터는 재처리하지 않음(무한 배치 반복 방지)
        new_data = [row for row in data if row.get("crawling_id") not in attempted_crawling_ids]
        if not new_data:
            logger.info("새로 처리할 데이터가 없습니다. 파이프라인을 종료합니다.")
            break
        data = new_data
        # merge 전에 원본 crawling_id를 모두 시도 처리해 중복 배치 반복 방지
        for row in data:
            if row.get("crawling_id") is not None:
                attempted_crawling_ids.add(row["crawling_id"])

        processed_data:list[dict] = data_pre.execute(data) #데이터 전처리

        for row in processed_data: #data를 하나씩 가져오면서 프롬프트를 생성
            row = crawling.attach_existing_post_context(row)

            type = crawling.CATEGORY_CD.get(row.get("category_cd"), "casual")
            prompt:str = Prompt.get_prompt(type, row) #프롬프트를 생성
            state = {
                "data": row,
                "prompt": prompt,
                "post": "",
                "embedding": [],
                "is_unique": True,
                "similar_posts": [],
                "status": "",
                "failed_crawling_id": None,
                "retry_count": 0,
                "max_retry": 2
            } #state 생성
            result = graph_compile.invoke(state)
            if result.get("status") != "passed":
                failed_id = result.get("failed_crawling_id")
                if failed_id is not None:
                    logger.warning(f"최종 실패(crawling_id={failed_id})")
                continue

            post_id = to_post(result["data"])
            if post_id is not None:
                to_post_vector(result["data"], post_id)
        logger.info(f"Batch {batch_count} completed...") #배치 완료
        batch_count += 1 #배치 카운트 증가


if __name__ == "__main__":
    run_pipeline()

