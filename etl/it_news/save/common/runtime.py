from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
import psycopg


STAGE_ROOT = Path(__file__).resolve().parents[1]
IT_NEWS_ROOT = STAGE_ROOT.parent
CLEANING_ROOT = IT_NEWS_ROOT / "cleaning"

LIMITS = {
    "title": 200,
    "thread": 20,
    "article_url": 500,
    "author": 100,
    "category_cd": 6,
}

INSERT_SQL = """
INSERT INTO "crawling" (
    title, content, thread, article_url, created_at,
    view_count, comment_count, point, author, map_id, category_cd
) VALUES (
    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
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


def make_stage_paths(bucket: str, run_at: datetime) -> StagePaths:
    """
    실행 일자 기준으로 스테이지의 성공/실패 디렉터리를 생성한다.

    Args:
        bucket: 생성할 하위 버킷 이름.
        run_at: 실행 기준 시각.

    Returns:
        생성된 디렉터리 경로 정보를 담은 StagePaths 객체.
    """
    base = STAGE_ROOT / bucket / run_at.strftime("%Y") / run_at.strftime("%m") / run_at.strftime("%d")
    success_dir = base / "success"
    fail_dir = base / "fail"
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
def cleaning_success_files(run_at: datetime) -> list[Path]:
    """
    지정한 날짜의 cleaning 성공 결과 CSV 목록을 조회한다.

    Args:
        run_at: 조회 기준 실행 시각.

    Returns:
        성공 디렉터리에 있는 CSV 파일 경로 목록.
    """
    base = CLEANING_ROOT / "cleaning" / run_at.strftime("%Y") / run_at.strftime("%m") / run_at.strftime("%d") / "success"
    if not base.is_dir():
        return []
    return sorted(base.glob("*.csv"))


def _env(name: str, default: str) -> str:
    """
    환경 변수를 읽고 비어 있으면 기본값을 반환한다.

    Args:
        name: 환경 변수 이름.
        default: 기본값.

    Returns:
        환경 변수 값 또는 기본값.
    """
    value = os.environ.get(name)
    return value if value not in (None, "") else default


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
    return psycopg.connect(
        host=_env("PGHOST", "localhost"),
        port=int(_env("PGPORT", "5432")),
        dbname=_env("PGDATABASE", "service"),
        user=_env("PGUSER", "user"),
        password=_env("PGPASSWORD", "password123"),
        connect_timeout=10,
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
        cur.execute('SELECT MAX("created_at") FROM "crawling"')
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
