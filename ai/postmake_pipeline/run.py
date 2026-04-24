from from_crawling import route_crawling_data
from prompt import get_prompt
from llm import graph

import time

CATEGORY_CD = {
    "IC02": "casual",
    "IC01": "formal",
}


def run_batch():
    while True:
        states:list[dict] = []
        data:list[dict] = route_crawling_data()
        for row in data:
            type = CATEGORY_CD.get(row["category_cd"])
            prompt:str = get_prompt(type, row)
            
            states.append({
                "data": row,
                "prompt": prompt
            })
            graph.invoke(states)

            time.sleep(1)


                
