"""BERT span 키워드 추출로 `analysis` 행의 `keywords`를 채운다."""

import logging

import pandas as pd

from common.bert_keywords import extract_keywords
from common.bert_tokenizer import BertTokenizer
from common.constant import AnalysisColumn, AnalyzeKeywordsConfig, CodeTable
from common.errors import PostAnalysisErrors
from postgresql.run_query import get_analysis_data, merge_analysis_data

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def analyze_keywords(max_rows: int | None = None) -> None:
    """빈 본문·IC02·키워드 기존값을 제외한 뒤 BERT span으로 `keywords`를 채우고 MERGE한다.

    Args:
        max_rows: 이번 실행에서 처리할 최대 행 수.
            ``None``(기본)이면 필터 후 **제한 없이** 전량 처리한다.
            값을 지정하면 상위 N건만 처리한다.

    Raises:
        ValueError: 필수 analysis 컬럼 누락.

    Note:
        함수 유형: A+D+F — 로컬 BERT 추출 + DB 조회·저장 + 배치
        안전성: Level 2 — ``analysis.keywords`` UPSERT
        불변 규칙: IC02 제외, 빈 content 제외, keywords·sentimental 결측 행 스킵
        에러 처리: 행별 추출 실패는 로그 후 continue, 성공분만 MERGE
        부작용: ``get_analysis_data`` SELECT, ``merge_analysis_data`` UPSERT
    """

    df = get_analysis_data()

    content_col = AnalysisColumn.CONTENT.value
    kw_col = AnalysisColumn.KEYWORDS.value
    info_col = AnalysisColumn.INFORMATION_CD.value
    sent_col = AnalysisColumn.SENTIMENTAL.value
    id_col = AnalysisColumn.CRAWLING_ID.value

    required = (content_col, kw_col, info_col, sent_col)
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(PostAnalysisErrors.AnalyzeKeywords.missing_columns(missing))

    empty_map = {k: pd.NA for k in AnalyzeKeywordsConfig.CONTENT_EMPTY_PLACEHOLDERS}
    c = df[content_col].replace(empty_map)
    df = df[c.notna() & c.astype(str).str.strip().ne("")]

    df = df[df[info_col] != CodeTable.INFORMATION_IT_INFO.value]
    df = df[df[kw_col].isnull()]
    df = df[df[sent_col].notna()]

    if df.empty:
        logger.info(PostAnalysisErrors.AnalyzeKeywords.no_pending_rows())
        return

    df[kw_col] = df[kw_col].astype(AnalyzeKeywordsConfig.DTYPE_OBJECT)

    if max_rows is not None and max_rows > 0:
        df = df.head(max_rows)
        logger.info("키워드 추출 상한 적용: %s건 처리 (max_rows=%s)", len(df), max_rows)

    classifier = BertTokenizer()
    total = len(df)

    for pos, (index, row) in enumerate(df.iterrows(), start=1):
        try:
            content = "" if pd.isna(row[content_col]) else str(row[content_col])
            sentimental = row[sent_col]
            df.at[index, kw_col] = extract_keywords(content, sentimental, classifier)
            logger.info("keywords: %s", df.at[index, kw_col])
        except Exception:
            crawling_id = row[id_col] if id_col in df.columns else index
            logger.exception(
                PostAnalysisErrors.AnalyzeKeywords.row_processing_failed(),
                crawling_id,
                index,
            )
            continue

        if pos % 20 == 0 or pos == total:
            logger.info("키워드 추출 진행: %d/%d", pos, total)

    merge_analysis_data(df)
    logger.info("키워드 추출 완료 (%s건)", total)


if __name__ == "__main__":
    analyze_keywords()
