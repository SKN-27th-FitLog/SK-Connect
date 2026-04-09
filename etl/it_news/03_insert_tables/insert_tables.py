"""
정제 CSV를 PostgreSQL \"crawling\" 테이블에 증분 삽입한다.
연결 확인 → MAX(created_at) → CSV 중 그보다 이후 행만 INSERT (crawling_id는 DB 시퀀스).
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import pandas as pd
import psycopg

# DB 컬럼 길이 (init.sql)
LIMITS = {
    "title": 200,
    "thread": 20,
    "article_url": 500,
    "author": 100,
    "category_cd": 6,
}

SQL_MAX_CREATED_AT = 'SELECT MAX("created_at") FROM "crawling"'

INSERT_SQL = """
INSERT INTO "crawling" (
    title, content, thread, article_url, created_at,
    view_count, comment_count, point, author, map_id, category_cd
) VALUES (
    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
)
"""


def _env(name: str, default: str) -> str:
    v = os.environ.get(name)
    return v if v is not None and v != "" else default


def get_connection_params() -> dict[str, Any]:
    return {
        "host": _env("PGHOST", "localhost"),
        "port": int(_env("PGPORT", "5432")),
        "dbname": _env("PGDATABASE", "service"),
        "user": _env("PGUSER", "user"),
        "password": _env("PGPASSWORD", "password123"),
    }


def check_connection() -> psycopg.Connection:
    params = get_connection_params()
    try:
        conn = psycopg.connect(**params, connect_timeout=10)
        conn.execute("SELECT 1")
        return conn
    except psycopg.Error as e:
        print(f"DB 연결 실패: {e}", file=sys.stderr)
        raise


def get_max_created_at(conn: psycopg.Connection) -> Optional[datetime]:
    with conn.cursor() as cur:
        cur.execute(SQL_MAX_CREATED_AT)
        row = cur.fetchone()
        return row[0] if row else None


def _empty_to_none(v: Any) -> Any:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    if isinstance(v, str) and v.strip() == "":
        return None
    return v


def _truncate(key: str, val: Any) -> Any:
    if val is None or not isinstance(val, str):
        return val
    lim = LIMITS.get(key)
    if lim is not None and len(val) > lim:
        return val[:lim]
    return val


def _row_tuple(row: pd.Series) -> tuple[Any, ...]:
    title = _truncate("title", _empty_to_none(row.get("title")))
    content = _empty_to_none(row.get("content"))
    thread = _truncate("thread", _empty_to_none(row.get("thread")))
    article_url = _truncate("article_url", _empty_to_none(row.get("article_url")))

    ca = row.get("created_at")
    ts = pd.to_datetime(ca, utc=True)
    if pd.isna(ts):
        raise ValueError("created_at 이 비어 있거나 파싱할 수 없습니다.")
    created_at = ts.to_pydatetime()

    vc = row.get("view_count")
    cc = row.get("comment_count")
    view_count = int(vc) if not pd.isna(vc) and vc is not None and str(vc).strip() != "" else None
    comment_count = int(cc) if not pd.isna(cc) and cc is not None and str(cc).strip() != "" else None

    pt = row.get("point")
    point = float(pt) if not pd.isna(pt) and pt is not None and str(pt).strip() != "" else None

    author = _truncate("author", _empty_to_none(row.get("author")))

    mid = _empty_to_none(row.get("map_id"))
    map_id: Optional[int]
    if mid is None:
        map_id = None
    else:
        try:
            map_id = int(float(mid))
        except (TypeError, ValueError):
            map_id = None

    cat = _truncate("category_cd", _empty_to_none(row.get("category_cd")))

    return (
        title,
        content,
        thread,
        article_url,
        created_at,
        view_count,
        comment_count,
        point,
        author,
        map_id,
        cat,
    )


def load_and_filter_csv(csv_path: Path, max_created_at: Optional[datetime]) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    if "created_at" not in df.columns:
        raise ValueError("CSV에 created_at 컬럼이 없습니다.")

    tseries = pd.to_datetime(df["created_at"], utc=True, errors="coerce")
    bad = tseries.isna()
    if bad.any():
        n = int(bad.sum())
        print(f"경고: created_at 파싱 실패 행 {n}건 제외", file=sys.stderr)
        df = df.loc[~bad].copy()
        tseries = tseries.loc[~bad]

    if df.empty:
        return df

    if max_created_at is None:
        return df

    max_ts = pd.Timestamp(max_created_at)
    if max_ts.tzinfo is None:
        max_cmp = max_ts.tz_localize("UTC")
    else:
        max_cmp = max_ts.tz_convert("UTC")

    mask = tseries > max_cmp
    return df.loc[mask].copy()


def insert_rows(conn: psycopg.Connection, df: pd.DataFrame) -> int:
    if df.empty:
        return 0

    rows: list[tuple[Any, ...]] = []
    for _, row in df.iterrows():
        rows.append(_row_tuple(row))

    with conn.cursor() as cur:
        cur.executemany(INSERT_SQL, rows)

    return len(rows)


def parse_args() -> argparse.Namespace:
    default_csv = (
        Path(__file__).resolve().parent.parent
        / "02_cleaning_tables"
        / "gatter_tables_260409.csv"
    )
    p = argparse.ArgumentParser(description="CSV를 crawling 테이블에 증분 삽입합니다.")
    p.add_argument(
        "--csv",
        type=Path,
        default=default_csv,
        help=f"삽입할 CSV 경로 (기본: {default_csv})",
    )
    return p.parse_args()


def main() -> int:
    args = parse_args()
    csv_path: Path = args.csv
    if not csv_path.is_file():
        print(f"CSV 파일이 없습니다: {csv_path}", file=sys.stderr)
        return 1

    try:
        conn = check_connection()
    except psycopg.Error:
        return 1

    try:
        max_at = get_max_created_at(conn)
        print(f"DB MAX(created_at) = {max_at!r}")

        df = load_and_filter_csv(csv_path, max_at)
        print(f"필터 후 삽입 대상 행 수: {len(df)} (원본 CSV 로드 후 증분 조건 적용)")

        n = insert_rows(conn, df)
        conn.commit()
        print(f"INSERT 완료: {n}건")
    except Exception as e:
        conn.rollback()
        print(f"오류: {e}", file=sys.stderr)
        return 1
    finally:
        conn.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())
