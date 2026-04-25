from from_crawling import route_crawling_data
from evaluation import evaluate_result
from prompt import get_prompt
from node import graph

import time

CATEGORY_CD = {
    "IC02": "food|casual",
    "IC01": "IT|formal",
}


def run_batch():
    batch_count = 0
    while True:
        states:list[dict] = []
        data:list[dict] = route_crawling_data() #crawling한 데이터를 가져옴
        for row in data: #data를 하나씩 가져오면서 프롬프트를 생성
            type = CATEGORY_CD.get(row["category_cd"])
            prompt:str = get_prompt(type, row) #프롬프트를 생성
            states.append({ "data": row, "prompt": prompt }) #states에 추가
            result = graph.invoke(states) #graph를 실행
            is_pass = evaluate_result(result)

            if is_pass:
                to_post(result)
                print(f"Batch {batch_count} completed...") #배치 완료 로그
            else:
                print(f"Batch {batch_count} failed...") #배치 실패 로그

        print(f"Batch {batch_count} completed...") #배치 완료 로그

        batch_count += 1 #배치 카운트 증가
        time.sleep(1) #1초 대기


                
