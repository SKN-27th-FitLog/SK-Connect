"""
정제 CSV를 PostgreSQL \"crawling\" 테이블에 증분 삽입한다.
연결 확인 → MAX(created_at) → CSV(단일 또는 여러 gatter_tables_*.csv 합본) 중
그 시각보다 이후 행만 INSERT (crawling_id는 DB 시퀀스).

여러 파일을 쓸 때도 비교 기준은 DB 전체의 MAX(created_at) 하나이며,
합친 뒤 동일한 created_at > max_at 조건으로 필터한다(파일이 나뉘어 있어도 증분 의미는 동일).
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
    '''환경 변수 name을 읽고 비어 있으면 default를 반환한다.'''
    v = os.environ.get(name)
    return v if v is not None and v != "" else default


def get_connection_params() -> dict[str, Any]:
    '''psycopg.connect에 넘길 호스트·포트·DB명·사용자·비밀번호 dict를 환경 변수에서 만든다.'''
    return {
        "host": _env("PGHOST", "localhost"),
        "port": int(_env("PGPORT", "5432")),
        "dbname": _env("PGDATABASE", "service"),
        "user": _env("PGUSER", "user"),
        "password": _env("PGPASSWORD", "password"),
    }


def check_connection() -> psycopg.Connection:
    '''DB에 연결해 SELECT 1로 확인한 뒤 연결 객체를 반환한다. 실패 시 메시지 출력 후 예외를 다시 던진다.'''
    params = get_connection_params()
    try:
        conn = psycopg.connect(**params, connect_timeout=10)
        conn.execute("SELECT 1")
        return conn
    except psycopg.Error as e:
        print(f"DB 연결 실패: {e}", file=sys.stderr)
        raise


def get_max_created_at(conn: psycopg.Connection) -> Optional[datetime]:
    '''crawling 테이블의 MAX(created_at) 한 건을 조회한다. 행이 없으면 None.'''
    with conn.cursor() as cur:
        cur.execute(SQL_MAX_CREATED_AT)
        row = cur.fetchone()
        return row[0] if row else None


def _empty_to_none(v: Any) -> Any:
    '''None·NaN·공백 문자열을 DB NULL에 맞게 None으로 정규화한다.'''
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    if isinstance(v, str) and v.strip() == "":
        return None
    return v


def _truncate(key: str, val: Any) -> Any:
    '''LIMITS에 정의된 컬럼별 최대 길이를 넘는 문자열을 앞부분만 잘라낸다.'''
    if val is None or not isinstance(val, str):
        return val
    lim = LIMITS.get(key)
    if lim is not None and len(val) > lim:
        return val[:lim]
    return val


def _row_tuple(row: pd.Series) -> tuple[Any, ...]:
    '''CSV 한 행을 INSERT 파라미터 튜플로 변환한다(자르기·날짜 UTC·숫자·map_id 정수화).'''
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


def filter_incremental_by_created_at(df: pd.DataFrame, max_created_at: Optional[datetime]) -> pd.DataFrame:
    '''created_at 파싱·정리 후 max_created_at보다 이후 행만 남긴다(증분 삽입 핵심).'''
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


def load_and_filter_csv(csv_path: Path, max_created_at: Optional[datetime]) -> pd.DataFrame:
    '''단일 CSV를 읽고 증분 필터를 적용한다.'''
    df = pd.read_csv(csv_path)
    return filter_incremental_by_created_at(df, max_created_at)


def load_and_filter_csv_paths(csv_paths: list[Path], max_created_at: Optional[datetime]) -> pd.DataFrame:
    '''여러 CSV를 순서대로 읽어 합친 뒤, 동일한 증분 기준으로 필터한다.

    여러 날짜 파일에 같은 article_url이 있으면 나중 경로(정렬상 뒤) 행을 남긴다.
    '''
    if not csv_paths:
        return pd.DataFrame()
    frames: list[pd.DataFrame] = []
    for p in csv_paths:
        frames.append(pd.read_csv(p))
    df = pd.concat(frames, ignore_index=True)
    if "article_url" in df.columns:
        before = len(df)
        df = df.drop_duplicates(subset=["article_url"], keep="last").reset_index(drop=True)
        dup = before - len(df)
        if dup:
            print(f"참고: 여러 CSV 간 article_url 중복 {dup}건 제거(마지막 출처 유지)", file=sys.stderr)
    return filter_incremental_by_created_at(df, max_created_at)


def default_gatter_csv_paths() -> list[Path]:
    '''02_cleaning_tables/gatter_tables_*.csv 경로를 이름순으로 반환한다.'''
    base = Path(__file__).resolve().parent.parent / "02_cleaning_tables"
    return sorted(base.glob("gatter_tables_*.csv"))


def insert_rows(conn: psycopg.Connection, df: pd.DataFrame) -> int:
    '''데이터프레임 각 행을 INSERT_SQL로 executemany 삽입하고 건수를 반환한다. 빈 프레임이면 0.'''
    if df.empty:
        return 0

    rows: list[tuple[Any, ...]] = []
    for _, row in df.iterrows():
        rows.append(_row_tuple(row))

    with conn.cursor() as cur:
        cur.executemany(INSERT_SQL, rows)

    return len(rows)


def parse_args() -> argparse.Namespace:
    '''삽입할 CSV 경로(--csv) 등 CLI 인자를 파싱한다.'''
    p = argparse.ArgumentParser(description="CSV를 crawling 테이블에 증분 삽입합니다.")
    p.add_argument(
        "--csv",
        nargs="*",
        type=Path,
        metavar="PATH",
        default=[],
        help=(
            "삽입할 CSV 경로(여러 개 가능). "
            "지정하지 않으면 02_cleaning_tables/gatter_tables_*.csv 전부(이름순)"
        ),
    )
    return p.parse_args()


def main() -> int:
    '''연결·MAX(created_at)·CSV 필터·INSERT·커밋까지 수행하고 종료 코드를 반환한다.'''
    args = parse_args()
    csv_paths: list[Path] = list(args.csv) if args.csv else default_gatter_csv_paths()
    if not csv_paths:
        print(
            "삽입할 CSV가 없습니다. --csv로 경로를 지정하거나 "
            "02_cleaning_tables/gatter_tables_*.csv 파일을 두세요.",
            file=sys.stderr,
        )
        return 1
    for p in csv_paths:
        if not p.is_file():
            print(f"CSV 파일이 없습니다: {p}", file=sys.stderr)
            return 1

    try:
        conn = check_connection()
    except psycopg.Error:
        return 1

    try:
        max_at = get_max_created_at(conn)
        print(f"DB MAX(created_at) = {max_at!r}")

        print(f"CSV 파일 {len(csv_paths)}개: {', '.join(str(p) for p in csv_paths)}")
        df = load_and_filter_csv_paths(csv_paths, max_at)
        print(f"필터 후 삽입 대상 행 수: {len(df)} (합본 후 created_at > MAX(created_at) 적용)")

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
