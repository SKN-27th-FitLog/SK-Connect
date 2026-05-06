# 로그 
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 패키지
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch
import torch.nn.functional as F
import pandas as pd

# 모듈
from common.postgresql.run_query import get_analysis_data, merge_analysis_data

# 사용할 모델 명 
MODEL_NAME = "sangrimlee/bert-base-multilingual-cased-nsmc"

# 토크나이저 로드
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

# 모델 로드
model = AutoModelForSequenceClassification.from_pretrained(MODEL_NAME)


def predict_sentiment(text: str) -> dict:
    inputs = tokenizer(
        text,
        return_tensors="pt",
        truncation=True,
        padding=True,
        max_length=512
    )

    with torch.no_grad():
        outputs = model(**inputs)
        probs = F.softmax(outputs.logits, dim=-1)[0]

    negative_score = probs[0].item()
    positive_score = probs[1].item()

    return {
        "sentimental": "positive" if positive_score >= negative_score else "negative",
        "score": round(max(positive_score, negative_score), 4),
        "positive_score": round(positive_score, 4),
        "negative_score": round(negative_score, 4)
    }


def analyze_sentimental():

    # 데이터 로드 
    df = get_analysis_data()

    # 데이터 중에서 IC02인 데이터 제외 (IC02는 감성분석 불가능한 데이터)
    df = df[df["category_cd"] != "IC02"]

    # 빈 칸이 있는 경우 오류 방지 
    df["sentimental"] = df["sentimental"].astype("object")
    df["score"] = df["score"].astype("float64")

    # for문으로 content 컬럼 값을 가져와서 predict_sentiment 함수로 감성분석 진행 
    # 감성분석 결과를 sentimental, score 컬럼에 적용한다. 
    for index, row in df.iterrows():
        text = row["content"]
        result = predict_sentiment(text)
        logger.info(result)
        df.at[index, "sentimental"] = result["sentimental"]
        df.at[index, "score"] = result["score"]

    # 처리 결과 데이터를 다시 analysis 테이블에 업데이트 
    merge_analysis_data(df)

    logger.info("데이터 적용 완료")




########################################################
if __name__ == "__main__":
    analyze_sentimental()