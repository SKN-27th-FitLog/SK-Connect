"""NSMC 학습 BERT로 `analysis` 행의 감성 라벨·점수를 채운다."""

# 로그
import logging

# 패키지
import pandas as pd

# 모듈
from common.bert_tokenizer import BertTokenizer
from common.constant import (
    AnalysisColumn,
    AnalyzeSentimentalConfig,
    CodeTable,
    SentimentResultKey,
)
from common.errors import PostAnalysisErrors
from postgresql.run_query import get_analysis_data, merge_analysis_data

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def analyze_sentimental() -> None:
    """``information_cd≠IC02`` 행 중 ``sentimental`` 또는 ``score`` 가 NULL인 행만 BERT 감성 분석 후 MERGE한다.

    Raises:
        ValueError: 필수 analysis 컬럼 누락.

    Note:
        함수 유형: A+D+F — 로컬 추론 + DB 조회·저장 + 배치
        안전성: Level 2 — ``analysis`` 감성·점수 컬럼 UPSERT
        불변 규칙: IC02(IT 정보) 제외, 이미 채워진 행 스킵
    """

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
        logger.info(PostAnalysisErrors.Sentiment.no_pending_rows())
        return

    df = df.loc[needs_mask].copy()
    logger.info(
        "감성 분석 대상 %s건 (sentimental 또는 score 중 NULL인 행)",
        pending,
    )

    # 빈 칸이 있는 경우 오류 방지
    df[sent_col] = df[sent_col].astype(AnalyzeSentimentalConfig.DTYPE_OBJECT)
    df[score_col] = df[score_col].astype(AnalyzeSentimentalConfig.DTYPE_SCORE)

    # Singleton: 최초 1회만 토크나이저·모델 로드 (`common/bert_tokenizer.py`)
    classifier = BertTokenizer()
    sk = SentimentResultKey
    # for문으로 content 컬럼 값을 가져와서 predict_sentiment로 감성분석 진행
    for index, row in df.iterrows():
        text = row[content_col]
        result = classifier.predict_sentiment(text)
        logger.info(result)
        df.at[index, sent_col] = result[sk.SENTIMENTAL.value]
        df.at[index, score_col] = result[sk.SCORE.value]

    # 처리 결과 데이터를 다시 analysis 테이블에 업데이트
    merge_analysis_data(df)

    logger.info("데이터 적용 완료 (%s건)", pending)


########################################################
if __name__ == "__main__":
    analyze_sentimental()
