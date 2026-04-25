from src.from_crawling import GetCrawlingData
from src.evaluation import evaluate_result
from src.data_pre import DataPreprocessing
from src.logging_config import set_logging
from src.prompt import Prompt
from src.to_post import to_post
from src.node import graph

logger = set_logging()


def run_batch():
    batch_count = 0
    failed_list = []
    while True:
        states:list[dict] = []
        data:list[dict] = GetCrawlingData.route_crawling_data() #crawling한 데이터를 가져옴
        if not data:
            logger.info("데이터가 없습니다.")
            break
        data_pre:list[dict] = DataPreprocessing.execute(data) #데이터 전처리
        for row in data_pre: #data를 하나씩 가져오면서 프롬프트를 생성
            type = GetCrawlingData.CATEGORY_CD.get(row["category_cd"])
            prompt:str = Prompt.get_prompt(type, row) #프롬프트를 생성
            states.append({ "data": row, "prompt": prompt }) #states에 추가
            result = graph.invoke(states) #graph를 실행
            is_pass = evaluate_result(result)

            if is_pass:
                to_post(result)
                print(f"게시글 생성 완료: {row['crawling_id']}") #게시글 생성 완료
            else: #평가 pass가 아닌 경우
                failed_list.append(row["crawling_id"])
                continue
        print(f"Batch {batch_count} completed...") #배치 완료
        batch_count += 1 #배치 카운트 증가

