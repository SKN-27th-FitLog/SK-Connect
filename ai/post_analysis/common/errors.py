"""post_analysis 배치·DB 검증용 사용자·로그·raise 메시지."""

from __future__ import annotations

from collections.abc import Iterable


def _missing_columns_message(
    source: str, task: str, missing: str | Iterable[str]
) -> str:
    """DataFrame/테이블 컬럼 누락 메시지."""
    cols_text = missing if isinstance(missing, str) else ", ".join(missing)
    return f"{source} 데이터에 {task}에 필요한 컬럼이 없습니다: {cols_text}"


class PostAnalysisErrors:
    """배치·DB 단계별 오류·로그 문구."""

    class Db:
        @staticmethod
        def connection_successful() -> str:
            return "Connection successful"

        @staticmethod
        def connection_failed(exc: BaseException) -> str:
            return f"Connection failed: {exc}"

    class Sentiment:
        @staticmethod
        def missing_columns(missing: Iterable[str]) -> str:
            return _missing_columns_message("analysis", "감성 분석", missing)

        @staticmethod
        def no_pending_rows() -> str:
            return (
                "감성·점수가 모두 채워져 처리할 행이 없습니다. "
                "(information_cd≠IC02(IT 정보) 제외 후 sentimental/score 결측 행 0건)"
            )

    class LlmKeywords:
        @staticmethod
        def missing_columns(missing: Iterable[str]) -> str:
            return _missing_columns_message("analysis", "LLM 키워드 추출", missing)

        @staticmethod
        def no_pending_rows() -> str:
            return "모든 row에 키워드가 존재합니다. 처리할 데이터가 없습니다."

        @staticmethod
        def row_processing_failed() -> str:
            """``logger.exception(PostAnalysisErrors.LlmKeywords.row_processing_failed(), title, index)``."""
            return "행 %s 처리 실패 (index=%s)"

    class GetReviews:
        @staticmethod
        def missing_crawling_columns(missing: Iterable[str]) -> str:
            return _missing_columns_message("crawling", "analysis 적재", missing)

        @staticmethod
        def missing_analysis_columns(missing: Iterable[str]) -> str:
            return _missing_columns_message("analysis", "crawling_id 중복 조회", missing)

        @staticmethod
        def no_rows_after_shop_resolve() -> str:
            return "shop 매칭 후 analysis 적재 대상 행이 없습니다."

        class Warn:
            """``logger.warning`` 수준 — 행 드랍 후 파이프라인은 계속 진행."""

            @staticmethod
            def shop_not_found(crawling_id: object, map_id: object) -> str:
                return (
                    f"shop 미매칭으로 행 제외 (crawling_id={crawling_id}, map_id={map_id})"
                )

            @staticmethod
            def ambiguous_shop(
                crawling_id: object, map_id: object, shop_count: int
            ) -> str:
                return (
                    f"shop 1:1이 아니어서 행 제외 "
                    f"(crawling_id={crawling_id}, map_id={map_id}, shop_count={shop_count})"
                )

    class Pipeline:
        @staticmethod
        def step_start(step: int, total: int, name: str) -> str:
            return f"{step}/{total} {name}"

        @staticmethod
        def step_failed(
            step: int, total: int, name: str, exc: BaseException
        ) -> str:
            return f"파이프라인 {step}/{total}단계({name}) 실패: {exc}"

        @staticmethod
        def completed() -> str:
            return "파이프라인 종료."

        @staticmethod
        def invalid_max_rows(value: int | None) -> str:
            return f"max_rows는 None 또는 0보다 큰 정수여야 합니다: {value!r}"
