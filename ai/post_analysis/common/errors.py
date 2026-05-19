"""post_analysis 배치·DB 검증용 사용자·로그·raise 메시지."""

from __future__ import annotations

from collections.abc import Iterable


def _missing_columns_message(task: str, missing: str | Iterable[str]) -> str:
    """``analysis`` DataFrame 컬럼 누락 메시지."""
    cols_text = missing if isinstance(missing, str) else ", ".join(missing)
    return f"analysis 데이터에 {task}에 필요한 컬럼이 없습니다: {cols_text}"


class PostAnalysisErrors:
    """배치 단계별 오류 문구."""

    class Sentiment:
        @staticmethod
        def missing_columns(missing: Iterable[str]) -> str:
            return _missing_columns_message("감성 분석", missing)

    class KiwiKeywords:
        @staticmethod
        def missing_columns(column: str) -> str:
            return _missing_columns_message("Kiwi 키워드 추출", column)

    class LlmKeywords:
        @staticmethod
        def missing_columns(column: str) -> str:
            return _missing_columns_message("LLM 키워드 추출", column)

    class ClassifyKeywords:
        @staticmethod
        def missing_columns(missing: Iterable[str]) -> str:
            return _missing_columns_message("키워드 분류", missing)
