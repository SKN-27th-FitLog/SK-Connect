from src.from_crawling import GetCrawlingData
from src.data_pre import DataPreprocessing
from src.logging_config import set_logging
from src.prompt import Prompt
from src.to_post import to_post, to_post_vector
from src.node import graph
logger = set_logging()


def _build_state(row: dict, prompt: str) -> dict:
    return {
        "data": row,
        "prompt": prompt,
        "post": "",
        "embedding": [],
        "is_unique": True,
        "similar_posts": [],
        "status": "",
        "failed_crawling_id": None,
        "retry_count": 0,
        "max_retry": 2,
    }


def run_pipeline():
    batch_count = 0
    attempted_crawling_ids: set[int] = set()
    crawling = GetCrawlingData()
    data_pre = DataPreprocessing()
    graph_compile = graph()

    while True:
        data: list[dict] = crawling.route_crawling_data()
        if not data:
            logger.info("데이터가 없습니다.")
            break

        new_data = [row for row in data if row.get("crawling_id") not in attempted_crawling_ids]
        if not new_data:
            logger.info("새로 처리할 데이터가 없습니다. 파이프라인을 종료합니다.")
            break
        data = new_data

        for row in data:
            if row.get("crawling_id") is not None:
                attempted_crawling_ids.add(row["crawling_id"])

        processed_data: list[dict] = data_pre.execute(data)

        for row in processed_data:
            crawling_id = row.get("crawling_id")
            logger.info(f"[ROW_START] crawling_id={crawling_id}")

            logger.info(f"[STEP] attach_existing_post_context crawling_id={crawling_id}")
            row = crawling.attach_existing_post_context(row)

            prompt_type = crawling.CATEGORY_CD.get(row.get("category_cd"), "casual")
            logger.info(f"[STEP] prompt_generation crawling_id={crawling_id} type={prompt_type}")
            prompt: str = Prompt.get_prompt(prompt_type, row)
            state = _build_state(row, prompt)
            logger.info(f"[STEP] graph_invoke_start crawling_id={crawling_id}")
            result = graph_compile.invoke(state)
            logger.info(
                f"[STEP] graph_invoke_done crawling_id={crawling_id} "
                f"status={result.get('status')}"
            )
            if result.get("status") != "passed":
                failed_id = result.get("failed_crawling_id")
                if failed_id is not None:
                    logger.warning(f"최종 실패(crawling_id={failed_id})")
                logger.info(f"[ROW_END] crawling_id={crawling_id} status={result.get('status')}")
                continue

            logger.info(f"[STEP] save_post_start crawling_id={crawling_id}")
            post_id = to_post(result["data"])
            if post_id is not None:
                logger.info(f"[STEP] save_vector_start crawling_id={crawling_id} post_id={post_id}")
                to_post_vector(result["data"], post_id)
            logger.info(f"[ROW_END] crawling_id={crawling_id} status=passed")
        logger.info(f"Batch {batch_count} completed...")
        logger.info(f"[BATCH_END] batch={batch_count}")
        batch_count += 1


if __name__ == "__main__":
    run_pipeline()

