from src.from_crawling import GetCrawlingData
from src.evaluation import evaluate_result
from src.data_pre import DataPreprocessing
from src.logging_config import set_logging
from src.prompt import Prompt
from src.to_post import to_post, to_post_vector
from src.node import graph
logger = set_logging()


def run_pipeline():
    batch_count = 0
    failed_list = []
    crawling = GetCrawlingData()
    data_pre = DataPreprocessing()
    graph_compile = graph()

    while True:
        data:list[dict] = crawling.route_crawling_data() #crawling한 데이터를 가져옴
        if not data:
            logger.info("데이터가 없습니다.")
            break #데이터가 없으면 종료

        processed_data:list[dict] = data_pre.execute(data) #데이터 전처리

        for row in processed_data: #data를 하나씩 가져오면서 프롬프트를 생성
            type = crawling.CATEGORY_CD.get(row["category_cd"])
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
            is_pass = evaluate_result(result)

            if is_pass:
                post_id = to_post(result["data"])
                if post_id is not None:
                    to_post_vector(result["data"], post_id)
                    print(f"게시글 생성 및 저장 완료: {row['crawling_id']}") #게시글 생성 완료
            elif not is_pass: #평가 pass가 아닌 경우
                if result.get("failed_crawling_id") is not None:
                    failed_list.append(result["failed_crawling_id"])

                continue
        print(f"Batch {batch_count} completed...") #배치 완료
        batch_count += 1 #배치 카운트 증가


if __name__ == "__main__":
    run_pipeline()

