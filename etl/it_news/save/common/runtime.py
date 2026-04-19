"""
save 스테이지 공통 런타임 유틸리티.

cleaning 성공 파일 탐색, DB 연결, 증분 필터링, INSERT 파라미터 정규화,
댓글 중복 키 조회처럼 저장 단계 전반에서 재사용하는 기능을 모아 둔다.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
import psycopg

from common.settings import env, get_config


######################
# 설정 기반 상수 및 SQL 관련
######################
CONFIG = get_config()
PATHS_CONFIG = CONFIG["paths"]
DB_CONFIG = CONFIG["db"]
COMMENTS_CONFIG = CONFIG["comments"]
LIMITS = CONFIG["limits"]
SUCCESS_DIRNAME = PATHS_CONFIG["success_dirname"]
FAIL_DIRNAME = PATHS_CONFIG["fail_dirname"]

STAGE_ROOT = Path(__file__).resolve().parents[1]
IT_NEWS_ROOT = STAGE_ROOT.parent
CLEANING_ROOT = IT_NEWS_ROOT / "cleaning"

INSERT_SQL = f"""
INSERT INTO "{DB_CONFIG["tables"]["crawling"]}" (
    title, content, thread, article_url, created_at,
    view_count, comment_count, point, author, map_id, category_cd
) VALUES (
    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
)
"""

COMMENT_INSERT_SQL = f"""
INSERT INTO "{DB_CONFIG["tables"]["comments"]}" (
    post_id, crawling_id, user_id, content, created_at, modify_at, status_cd
) VALUES (
    %s, %s, %s, %s, %s, %s, %s
)
"""


######################
# 스테이지 경로 관리 관련
######################
@dataclass(frozen=True)
class StagePaths:
    """
    save 단계의 성공/실패 출력 디렉터리를 묶어 보관한다.

    Attributes:
        success_dir: 성공 결과 CSV 저장 디렉터리.
        fail_dir: 실패 결과 CSV 및 로그 저장 디렉터리.
    """
    success_dir: Path
    fail_dir: Path


def make_stage_paths(bucket: str, run_at: datetime, *, kind: str | None = None) -> StagePaths:
    """
    실행 일자 기준으로 스테이지의 성공/실패 디렉터리를 생성한다.

    Args:
        bucket: 생성할 하위 버킷 이름.
        run_at: 실행 기준 시각.

    Returns:
        생성된 디렉터리 경로 정보를 담은 StagePaths 객체.
    """
    # save 산출물도 다른 스테이지와 동일한 날짜 기반 디렉터리 규칙을 사용한다.
    base = STAGE_ROOT / bucket
    if kind:
        base = base / kind
    base = base / run_at.strftime("%Y") / run_at.strftime("%m") / run_at.strftime("%d")
    success_dir = base / SUCCESS_DIRNAME
    fail_dir = base / FAIL_DIRNAME
    success_dir.mkdir(parents=True, exist_ok=True)
    fail_dir.mkdir(parents=True, exist_ok=True)
    return StagePaths(success_dir=success_dir, fail_dir=fail_dir)


def source_csv_path(paths: StagePaths, filename: str, *, ok: bool) -> Path:
    """
    성공/실패 여부에 따라 대상 CSV 저장 경로를 계산한다.

    Args:
        paths: 스테이지 디렉터리 정보.
        filename: 저장할 파일명.
        ok: 성공 결과 저장 여부.

    Returns:
        최종 CSV 파일 경로.
    """
    return (paths.success_dir if ok else paths.fail_dir) / filename


def log_path(paths: StagePaths, filename: str) -> Path:
    """
    실패 처리 시 사용할 로그 파일 경로를 계산한다.

    Args:
        paths: 스테이지 디렉터리 정보.
        filename: 원본 파일명.

    Returns:
        실패 로그 파일 경로.
    """
    return paths.fail_dir / f"{Path(filename).stem}.log"


######################
# 입력 파일 조회 및 환경 변수 처리 관련
######################
def cleaning_success_files(run_at: datetime, *, kind: str | None = None) -> list[Path]:
    """
    지정한 날짜의 cleaning 성공 결과 CSV 목록을 조회한다.

    Args:
        run_at: 조회 기준 실행 시각.

    Returns:
        성공 디렉터리에 있는 CSV 파일 경로 목록.
    """
    # save 입력은 항상 cleaning 성공 CSV를 기준으로 탐색한다.
    base = CLEANING_ROOT / PATHS_CONFIG["cleaning_bucket"]
    if kind:
        base = base / kind
    base = base / run_at.strftime("%Y") / run_at.strftime("%m") / run_at.strftime("%d") / SUCCESS_DIRNAME
    if not base.is_dir():
        return []
    return sorted(base.glob("*.csv"))


######################
# DB 연결 및 증분 적재 기준 조회 관련
######################
def connect() -> psycopg.Connection:
    """
    PostgreSQL 데이터베이스에 연결한다.

    Args:
        없음.

    Returns:
        psycopg 연결 객체.
    """
    # 비밀값은 `.env`에서 읽고, 코드는 로컬 fallback만 제공한다.
    host = env("PGHOST", "localhost")
    port = int(env("PGPORT", "5432"))
    dbname = env("PGDATABASE", "service")
    user = env("PGUSER", "user")
    password = env("PGPASSWORD", "password")
    return psycopg.connect(
        host=host,
        port=port,
        dbname=dbname,
        user=user,
        password=password,
        connect_timeout=DB_CONFIG["connect_timeout"],
    )


def get_max_created_at(conn: psycopg.Connection) -> datetime | None:
    """
    DB에 저장된 가장 최근 created_at 값을 조회한다.

    Args:
        conn: 활성화된 DB 연결 객체.

    Returns:
        조회된 최신 created_at 또는 데이터가 없으면 None.
    """
    with conn.cursor() as cur:
        cur.execute(f'SELECT MAX("created_at") FROM "{DB_CONFIG["tables"]["crawling"]}"')
        row = cur.fetchone()
        return row[0] if row else None


def filter_incremental(df: pd.DataFrame, max_created_at: datetime | None) -> pd.DataFrame:
    """
    기존 DB 적재 시각 이후 데이터만 남기도록 DataFrame을 필터링한다.

    Args:
        df: 원본 데이터프레임.
        max_created_at: DB에 이미 저장된 최신 created_at 값.

    Returns:
        증분 적재 대상만 남긴 데이터프레임.
    """
    if df.empty:
        return df
    # parsing 실패한 created_at은 증분 비교가 불가능하므로 먼저 제외한다.
    created = pd.to_datetime(df["created_at"], utc=True, errors="coerce")
    df = df.loc[~created.isna()].copy()
    created = created.loc[df.index]
    if max_created_at is None:
        return df
    max_ts = pd.Timestamp(max_created_at)
    if max_ts.tzinfo is None:
        max_ts = max_ts.tz_localize("UTC")
    else:
        max_ts = max_ts.tz_convert("UTC")
    return df.loc[created > max_ts].copy()


######################
# DB 적재용 값 정규화 관련
######################
def _empty_to_none(value: Any) -> Any:
    """
    빈 문자열, NaN, None 값을 DB 적재용 None으로 통일한다.

    Args:
        value: 정규화할 값.

    Returns:
        정규화된 값.
    """
    if value is None:
        return None
    if isinstance(value, float) and pd.isna(value):
        return None
    if isinstance(value, str) and value.strip() == "":
        return None
    return value


def _truncate(key: str, value: Any) -> Any:
    """
    컬럼별 최대 길이 제한에 맞춰 문자열 값을 자른다.

    Args:
        key: 길이 제한을 조회할 컬럼명.
        value: 잘라낼 값.

    Returns:
        길이 제한이 적용된 값.
    """
    # 길이 제한은 문자열 컬럼에만 적용한다.
    if not isinstance(value, str):
        return value
    limit = LIMITS.get(key)
    if limit is None or len(value) <= limit:
        return value
    return value[:limit]


def row_tuple(row: pd.Series) -> tuple[Any, ...]:
    """
    DataFrame 한 행을 SQL INSERT 파라미터 튜플로 변환한다.

    Args:
        row: 적재할 단일 데이터 행.

    Returns:
        INSERT_SQL 순서에 맞춘 값 튜플.
    """
    created_at = pd.to_datetime(row["created_at"], utc=True, errors="raise").to_pydatetime()
    map_id = _empty_to_none(row.get("map_id"))
    if map_id is not None:
        try:
            map_id = int(float(map_id))
        except (TypeError, ValueError):
            map_id = None

    # INSERT 순서는 SQL 컬럼 순서와 반드시 일치해야 하므로 튜플 생성 로직을 한곳에 모은다.
    return (
        _truncate("title", _empty_to_none(row.get("title"))),
        _empty_to_none(row.get("content")),
        _truncate("thread", _empty_to_none(row.get("thread"))),
        _truncate("article_url", _empty_to_none(row.get("article_url"))),
        created_at,
        _empty_to_none(row.get("view_count")),
        _empty_to_none(row.get("comment_count")),
        _empty_to_none(row.get("point")),
        _truncate("author", _empty_to_none(row.get("author"))),
        map_id,
        _truncate("category_cd", _empty_to_none(row.get("category_cd"))),
    )


def insert_dataframe(conn: psycopg.Connection, df: pd.DataFrame) -> int:
    """
    DataFrame 전체를 DB에 일괄 INSERT 한다.

    Args:
        conn: 활성화된 DB 연결 객체.
        df: 적재할 데이터프레임.

    Returns:
        실제로 적재한 행 수.
    """
    if df.empty:
        return 0
    rows = [row_tuple(row) for _, row in df.iterrows()]
    with conn.cursor() as cur:
        cur.executemany(INSERT_SQL, rows)
    return len(rows)


def _normalize_comment_datetime(value: Any) -> str:
    """
    댓글 생성/수정 시각을 UTC 기준 ISO 문자열로 정규화한다.

    Args:
        value: 정규화할 원본 시각 값.

    Returns:
        비교용 ISO 문자열.
    """
    return pd.to_datetime(value, utc=True, errors="raise").isoformat()


def _parse_int_field(value: Any) -> int | None:
    """
    DB 적재용 숫자 필드를 int 또는 None으로 정규화한다.

    Args:
        value: 정규화할 원본 값.

    Returns:
        정수 값 또는 None.
    """
    normalized = _empty_to_none(value)
    if normalized is None:
        return None
    return int(float(normalized))


def comment_row_tuple(row: pd.Series, *, user_id: int) -> tuple[Any, ...]:
    """
    댓글 DataFrame 한 행을 comments INSERT 파라미터 튜플로 변환한다.

    Args:
        row: 적재할 단일 댓글 행.
        user_id: comments.user_id 에 넣을 기본 사용자 ID.

    Returns:
        COMMENT_INSERT_SQL 순서에 맞춘 값 튜플.
    """
    created_at = pd.to_datetime(row["created_at"], utc=True, errors="raise").to_pydatetime()
    modify_at = pd.to_datetime(row["modify_at"], utc=True, errors="raise").to_pydatetime()
    # 댓글 상태 코드는 설정된 기본값과 최대 길이를 공통 적용한다.
    return (
        _parse_int_field(row.get("post_id")),
        _parse_int_field(row.get("crawling_id")),
        user_id,
        _empty_to_none(row.get("content")),
        created_at,
        modify_at,
        str(_empty_to_none(row.get("status_cd")) or COMMENTS_CONFIG["default_status_cd"])[
            : COMMENTS_CONFIG["status_cd_max_length"]
        ],
    )


def insert_comment_dataframe(conn: psycopg.Connection, df: pd.DataFrame, *, user_id: int) -> int:
    """
    댓글 DataFrame 전체를 DB에 일괄 INSERT 한다.

    Args:
        conn: 활성화된 DB 연결 객체.
        df: 적재할 댓글 데이터프레임.
        user_id: comments.user_id 에 넣을 기본 사용자 ID.

    Returns:
        실제로 적재한 행 수.
    """
    if df.empty:
        return 0
    rows = [comment_row_tuple(row, user_id=user_id) for _, row in df.iterrows()]
    # DB에 이미 같은 댓글이 있는지 확인하기 위해 키 컬럼만 조회한다.
    with conn.cursor() as cur:
        cur.executemany(COMMENT_INSERT_SQL, rows)
    return len(rows)


def existing_comment_keys(conn: psycopg.Connection, crawling_ids: list[int]) -> set[tuple[int, str, str]]:
    """
    지정한 crawling_id 목록에 대해 이미 저장된 댓글 키를 조회한다.

    Args:
        conn: 활성화된 DB 연결 객체.
        crawling_ids: 비교 대상 crawling_id 목록.

    Returns:
        (crawling_id, created_at_iso, content) 조합의 집합.
    """
    if not crawling_ids:
        return set()

    with conn.cursor() as cur:
        cur.execute(
            f"""
            SELECT crawling_id, created_at, content
            FROM "{DB_CONFIG["tables"]["comments"]}"
            WHERE crawling_id = ANY(%s)
            """,
            (crawling_ids,),
        )
        rows = cur.fetchall()

    keys: set[tuple[int, str, str]] = set()
    for crawling_id, created_at, content in rows:
        if crawling_id is None or created_at is None or content is None:
            continue
        keys.add((int(crawling_id), _normalize_comment_datetime(created_at), str(content).strip()))
    return keys


def filter_existing_comments(df: pd.DataFrame, existing_keys: set[tuple[int, str, str]]) -> pd.DataFrame:
    """
    이미 DB에 저장된 댓글과 동일한 키를 가진 행을 제외한다.

    Args:
        df: 원본 댓글 데이터프레임.
        existing_keys: DB에서 조회한 기존 댓글 키 집합.

    Returns:
        신규 댓글만 남긴 데이터프레임.
    """
    if df.empty or not existing_keys:
        return df

    keep_indexes: list[int] = []
    for index, row in df.iterrows():
        key = (
            int(float(row["crawling_id"])),
            _normalize_comment_datetime(row["created_at"]),
            str(row["content"]).strip(),
        )
        if key not in existing_keys:
            keep_indexes.append(index)
    return df.loc[keep_indexes].copy()
