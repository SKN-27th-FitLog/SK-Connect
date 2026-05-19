"""ETL 에러 코드·메시지 중앙 관리."""

from __future__ import annotations


class EtlErrors:
    """에러 코드 = 중첩 클래스·메서드명. 메시지는 classmethod로 반환."""

    class Crawl:
        @classmethod
        def created_at_not_found(cls) -> str:
            return "작성일자를 찾을 수 없습니다."

    class Watermark:
        @classmethod
        def unsupported_service(cls, service: object) -> str:
            return (
                "get_last_success_date: GEEKNEWS / PYTORCH만 service로 지정 가능 "
                f"(전체는 None, 받은 값={service!r})"
            )

    class Preprocess:
        @classmethod
        def missing_columns_on_load(cls) -> str:
            return "성공 CSV 로드: created_at/thread 컬럼 없음 — 중단"

        @classmethod
        def raw_root_missing(cls, path: object) -> str:
            return f"get_crawling_success_for_cleaning: process=raw 루트 없음 {path}"

        @classmethod
        def no_crawling_csv(cls, service: str) -> str:
            return (
                "get_crawling_success_for_cleaning: 조건에 맞는 성공 CSV 없음 "
                f"(service={service})"
            )

        @classmethod
        def cleaning_root_missing(cls, path: object) -> str:
            return f"get_cleaning_success_for_save: process=cleaning 루트 없음 {path}"

        @classmethod
        def no_cleaning_csv(cls) -> str:
            return "get_cleaning_success_for_save: 조건에 맞는 성공 CSV 없음 (cleaning 산출)"

    class Save:
        @classmethod
        def merge_insert_failed(cls) -> str:
            return "save: crawling 일괄 MERGE·INSERT 실패 — 전부 fail 처리"

    class Db:
        @classmethod
        def connection_failed(cls, detail: str) -> str:
            return f"Connection failed: {detail}"
