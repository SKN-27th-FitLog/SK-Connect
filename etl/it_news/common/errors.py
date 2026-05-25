"""ETL 에러 코드·메시지 중앙 관리."""

from __future__ import annotations


class EtlErrors:
    """ETL 에러 메시지 팩토리(중첩 클래스·classmethod).

    Note:
        함수 유형: B — 메시지 문자열 조립
        안전성: Level 0 — I/O·DB 없음
        불변 규칙: 로그·raise·fail CSV에 동일 문구 재사용
    """

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

        @classmethod
        def missing_env_var(cls, key: str) -> str:
            return f"필수 환경변수가 설정되지 않았습니다: {key} (etl/it_news/.env 확인)"
