"""post_analysis 배치·DB 검증용 사용자·로그·raise 메시지."""

from __future__ import annotations

from collections.abc import Iterable


def _missing_columns_message(
    source: str, task: str, missing: str | Iterable[str]
) -> str:
    """DataFrame/테이블 컬럼 누락 시 ``ValueError`` 등에 쓸 메시지 문자열을 만든다.

    Args:
        source: 데이터 출처 표시 (예: ``crawling``, ``analysis``).
        task: 수행 중이던 작업명.
        missing: 누락 컬럼명(들).

    Returns:
        사람이 읽을 수 있는 한 줄 오류 메시지.

    Note:
        함수 유형: B — 데이터 변환 (문자열 포맷)
        안전성: Level 0 — 부작용 없음
    """
    cols_text = missing if isinstance(missing, str) else ", ".join(missing)
    return f"{source} 데이터에 {task}에 필요한 컬럼이 없습니다: {cols_text}"


class PostAnalysisErrors:
    """배치·DB 단계별 오류·로그 문구."""

    class Db:
        """DB 연결 검증 로그·반환 메시지 (Level 0, 유형 B)."""

        @staticmethod
        def connection_successful() -> str:
            """연결 성공 시 ``test_conn`` 반환 문자열."""
            return "Connection successful"

        @staticmethod
        def connection_failed(exc: BaseException) -> str:
            """연결 실패 시 예외를 포함한 반환 문자열."""
            return f"Connection failed: {exc}"

    class Sentiment:
        """``analyze_sentimental`` 단계 오류·정보 메시지 (Level 0, 유형 B)."""

        @staticmethod
        def missing_columns(missing: Iterable[str]) -> str:
            """필수 analysis 컬럼 누락 ``ValueError`` 메시지."""
            return _missing_columns_message("analysis", "감성 분석", missing)

        @staticmethod
        def no_pending_rows() -> str:
            """처리 대상 0건일 때 ``logger.info`` 메시지."""
            return (
                "감성·점수가 모두 채워져 처리할 행이 없습니다. "
                "(information_cd≠IC02(IT 정보) 제외 후 sentimental/score 결측 행 0건)"
            )

        @staticmethod
        def no_processable_rows() -> str:
            """pending은 있으나 본문 없음 등으로 처리 가능 행 0건일 때 ``logger.info`` 메시지."""
            return "감성 분석 처리 가능한 행이 없습니다. (본문 없음 등으로 제외)"

        @staticmethod
        def excluded_empty_content(count: int) -> str:
            """빈 본문 제외 건수 ``logger.info`` 메시지."""
            return f"본문 없음으로 감성 분석 제외: {count}건"

    class LlmKeywords:
        """``analyze_keywords_by_llm`` 단계 오류·로그 메시지 (Level 0, 유형 B)."""

        @staticmethod
        def missing_columns(missing: Iterable[str]) -> str:
            """필수 analysis 컬럼 누락 ``ValueError`` 메시지."""
            return _missing_columns_message("analysis", "LLM 키워드 추출", missing)

        @staticmethod
        def no_pending_rows() -> str:
            """키워드 미충족 행 0건일 때 ``logger.info`` 메시지."""
            return "모든 row에 키워드가 존재합니다. 처리할 데이터가 없습니다."

        @staticmethod
        def row_processing_failed() -> str:
            """행별 LLM 실패 ``logger.exception`` 포맷 문자열."""
            return "행 %s 처리 실패 (index=%s)"

    class AnalyzeKeywords:
        """``analyze_keywords`` 단계 오류·로그 메시지 (Level 0, 유형 B)."""

        @staticmethod
        def missing_columns(missing: Iterable[str]) -> str:
            """필수 analysis 컬럼 누락 ``ValueError`` 메시지."""
            return _missing_columns_message("analysis", "BERT 키워드 추출", missing)

        @staticmethod
        def no_pending_rows() -> str:
            """키워드 미충족 행 0건일 때 ``logger.info`` 메시지."""
            return "모든 row에 키워드가 존재합니다. 처리할 데이터가 없습니다."

        @staticmethod
        def row_processing_failed() -> str:
            """행별 BERT 키워드 추출 실패 ``logger.exception`` 포맷 문자열."""
            return "crawling_id=%s 처리 실패 (index=%s)"

    class ItKeywords:
        """``analyze_it_keywords`` 단계 오류·로그 메시지 (Level 0, 유형 B)."""

        @staticmethod
        def missing_columns(missing: Iterable[str]) -> str:
            """필수 analysis 컬럼 누락 ``ValueError`` 메시지."""
            return _missing_columns_message("analysis", "IT 키워드 추출", missing)

        @staticmethod
        def no_pending_rows() -> str:
            """IC02 키워드 처리 대상 0건일 때 ``logger.info`` 메시지."""
            return "IC02 IT 키워드 처리할 행이 없습니다."

        @staticmethod
        def no_successful_rows() -> str:
            """행별 처리 후 저장 가능한 성공 행 0건일 때 ``logger.info`` 메시지."""
            return "IC02 IT 키워드 성공 행이 없어 MERGE를 생략합니다."

        @staticmethod
        def row_processing_failed() -> str:
            """행별 IC02 키워드 추출 실패 ``logger.exception`` 포맷 문자열."""
            return "IC02 IT 키워드 처리 실패 (crawling_id=%s, index=%s)"

    class GetReviews:
        """``get_reviews`` 단계 오류·정보 메시지 (Level 0, 유형 B)."""

        @staticmethod
        def missing_crawling_columns(missing: Iterable[str]) -> str:
            """crawling 필수 컬럼 누락 ``ValueError`` 메시지."""
            return _missing_columns_message("crawling", "analysis 적재", missing)

        @staticmethod
        def missing_analysis_columns(missing: Iterable[str]) -> str:
            """analysis ``crawling_id`` 컬럼 누락 ``ValueError`` 메시지."""
            return _missing_columns_message("analysis", "crawling_id 중복 조회", missing)

        @staticmethod
        def no_rows_after_shop_resolve() -> str:
            """shop 매칭·필터 후 적재 대상 0건 ``logger.info`` 메시지."""
            return "shop 매칭 후 analysis 적재 대상 행이 없습니다."

        class Warn:
            """``logger.warning`` 수준 — 행 드랍 후 파이프라인은 계속 진행 (Level 0, 유형 B)."""

            @staticmethod
            def shop_not_found(crawling_id: object, map_id: object) -> str:
                """``map_id``에 대응 shop 없음·결측 시 warning 메시지."""
                return (
                    f"shop 미매칭으로 행 제외 (crawling_id={crawling_id}, map_id={map_id})"
                )

            @staticmethod
            def ambiguous_shop(
                crawling_id: object, map_id: object, shop_count: int
            ) -> str:
                """동일 ``map_id``에 shop 2건 이상일 때 warning 메시지."""
                return (
                    f"shop 1:1이 아니어서 행 제외 "
                    f"(crawling_id={crawling_id}, map_id={map_id}, shop_count={shop_count})"
                )

    class Pipeline:
        """``run_pipeline`` 오케스트레이션 로그·검증 메시지 (Level 0, 유형 B)."""

        @staticmethod
        def step_start(step: int, total: int, name: str) -> str:
            """단계 시작 ``logger.info`` 메시지."""
            return f"{step}/{total} {name}"

        @staticmethod
        def step_failed(
            step: int, total: int, name: str, exc: BaseException
        ) -> str:
            """단계 실패 ``logger.error`` 메시지."""
            return f"파이프라인 {step}/{total}단계({name}) 실패: {exc}"

        @staticmethod
        def completed() -> str:
            """전 단계 성공 후 ``logger.info`` 메시지."""
            return "파이프라인 종료."

        @staticmethod
        def invalid_max_rows(value: int | None) -> str:
            """``max_rows`` 검증 실패 ``ValueError`` 메시지."""
            return f"max_rows는 None 또는 0보다 큰 정수여야 합니다: {value!r}"
