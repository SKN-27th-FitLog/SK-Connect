"""NSMC 학습 BERT로 `analysis` 행의 감성 라벨·점수를 채운다."""

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
from common.constant import (
    AnalysisColumn,
    AnalyzeSentimentalConfig,
    CodeTable,
    SentimentLabel,
    SentimentResultKey,
)
from common.errors import PostAnalysisErrors
from postgresql.run_query import get_analysis_data, merge_analysis_data

# 사용할 모델 명 
MODEL_NAME = AnalyzeSentimentalConfig.MODEL_NAME

# 토크나이저 로드
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

# 모델 로드
model = AutoModelForSequenceClassification.from_pretrained(MODEL_NAME)


def predict_sentiment(text: str) -> dict:
    """단일 텍스트에 대해 긍·부정 확률을 구하고 대표 라벨·점수 dict를 반환한다.

    Args:
        text: 리뷰 본문 등 분류 대상 문자열.

    Returns:
        `SentimentResultKey` 값을 키로 하는 라벨·신뢰도·각 클래스 확률.
    """
    inputs = tokenizer(
        text,
        return_tensors="pt",
        truncation=True,
        padding=True,
        max_length=AnalyzeSentimentalConfig.MAX_SEQUENCE_LENGTH
    )

    with torch.no_grad():
        outputs = model(**inputs)
        probs = F.softmax(outputs.logits, dim=-1)[0]

    negative_score = probs[0].item()
    positive_score = probs[1].item()
    dec = AnalyzeSentimentalConfig.SCORE_DECIMAL_PLACES
    sk = SentimentResultKey
    label = (
        SentimentLabel.POSITIVE.value
        if positive_score >= negative_score
        else SentimentLabel.NEGATIVE.value
    )

    return {
        sk.SENTIMENTAL.value: label,
        sk.SCORE.value: round(max(positive_score, negative_score), dec),
        sk.POSITIVE_SCORE.value: round(positive_score, dec),
        sk.NEGATIVE_SCORE.value: round(negative_score, dec),
    }


def analyze_sentimental() -> None:
    """``information_cd`` 가 IT 정보(IC02)가 아닌 행만 대상으로, ``sentimental`` 또는 ``score`` 가 NULL인 행만 계산해 MERGE한다."""

    content_col = AnalysisColumn.CONTENT.value
    info_col = AnalysisColumn.INFORMATION_CD.value
    sent_col = AnalysisColumn.SENTIMENTAL.value
    score_col = AnalysisColumn.SCORE.value

    required = (content_col, sent_col, score_col, info_col)

    # 데이터 로드
    df = get_analysis_data()

    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(PostAnalysisErrors.Sentiment.missing_columns(missing))

    # information_cd 기준 IC02(IT 정보글) 제외 — category_cd(CA*) 축과 별개
    df = df[df[info_col] != CodeTable.INFORMATION_IT_INFO.value]

    # sentimental · score 둘 다 채워진 행은 스킵 (재전체 처리 방지)
    needs_mask = df[sent_col].isna() | df[score_col].isna()
    pending = int(needs_mask.sum())

    if pending == 0:
        logger.info(
            "감성·점수가 모두 채워져 처리할 행이 없습니다. "
            "(information_cd≠IC02(IT 정보) 제외 후 sentimental/score 결측 행 0건)"
        )
        return

    df = df.loc[needs_mask].copy()
    logger.info(
        "감성 분석 대상 %s건 (sentimental 또는 score 중 NULL인 행)",
        pending,
    )

    # 빈 칸이 있는 경우 오류 방지
    df[sent_col] = df[sent_col].astype(AnalyzeSentimentalConfig.DTYPE_OBJECT)
    df[score_col] = df[score_col].astype(AnalyzeSentimentalConfig.DTYPE_SCORE)

    # for문으로 content 컬럼 값을 가져와서 predict_sentiment 함수로 감성분석 진행
    sk = SentimentResultKey
    for index, row in df.iterrows():
        text = row[content_col]
        result = predict_sentiment(text)
        logger.info(result)
        df.at[index, sent_col] = result[sk.SENTIMENTAL.value]
        df.at[index, score_col] = result[sk.SCORE.value]

    # 처리 결과 데이터를 다시 analysis 테이블에 업데이트
    merge_analysis_data(df)

    logger.info("데이터 적용 완료 (%s건)", pending)




########################################################
if __name__ == "__main__":
    analyze_sentimental()
