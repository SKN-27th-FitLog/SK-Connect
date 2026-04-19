from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

from common.runtime import (
    cleaning_success_files,
    connect,
    filter_incremental,
    get_max_created_at,
    insert_dataframe,
    log_path,
    make_stage_paths,
    source_csv_path,
)


_KST = ZoneInfo("Asia/Seoul")


######################
# 실행 인자 및 실행 시각 처리 관련
######################
def parse_args() -> argparse.Namespace:
    """
    save 스테이지 실행 인자를 파싱한다.

    Args:
        없음.

    Returns:
        실행 날짜를 포함한 argparse 네임스페이스.
    """
    parser = argparse.ArgumentParser(description="IT News save stage runner")
    parser.add_argument("--date", default=None, help="기본값은 오늘(KST), YYYY-MM-DD 형식")
    return parser.parse_args()


def parse_run_at(date_arg: str | None) -> datetime:
    """
    입력된 날짜 문자열을 KST 기준 실행 시각으로 변환한다.

    Args:
        date_arg: YYYY-MM-DD 형식의 날짜 문자열. 없으면 현재 시각을 사용한다.

    Returns:
        KST timezone 정보가 포함된 datetime 객체.
    """
    if not date_arg:
        return datetime.now(_KST)
    return datetime.strptime(date_arg, "%Y-%m-%d").replace(tzinfo=_KST)


######################
# 결과 파일 저장 관련
######################
def write_dataframe(path: Path, df: pd.DataFrame) -> None:
    """
    DataFrame을 UTF-8 BOM이 포함된 CSV 파일로 저장한다.

    Args:
        path: 저장 대상 CSV 경로.
        df: 저장할 데이터프레임.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig")


######################
# save 실행 흐름 관련
######################
def main() -> int:
    """
    cleaning 성공 파일을 읽어 DB에 적재하고 결과 파일을 기록한다.

    Args:
        없음.

    Returns:
        정상 종료 시 0, DB 연결 실패 시 1.
    """
    args = parse_args()
    run_at = parse_run_at(args.date)
    save_paths = make_stage_paths("save", run_at)
    files = cleaning_success_files(run_at)
    if not files:
        raise SystemExit("save 대상 cleaning 성공 파일이 없습니다.")

    try:
        conn = connect()
    except Exception as exc:
        print(f"DB 연결 실패: {exc}")
        return 1

    try:
        baseline_max_created_at = get_max_created_at(conn)
        print(f"DB MAX(created_at) = {baseline_max_created_at!r}")

        for file_path in files:
            df = pd.read_csv(file_path)
            filtered = filter_incremental(df, baseline_max_created_at)
            success_path = source_csv_path(save_paths, file_path.name, ok=True)
            fail_path = source_csv_path(save_paths, file_path.name, ok=False)

            try:
                inserted = insert_dataframe(conn, filtered)
                conn.commit()
                write_dataframe(success_path, filtered)
                print(f"[ok] {file_path.name}: {inserted} rows -> {success_path}")
            except Exception as exc:
                conn.rollback()
                write_dataframe(fail_path, df)
                log_path(save_paths, file_path.name).write_text(str(exc), encoding="utf-8")
                print(f"[fail] {file_path.name}: {exc}")
    finally:
        conn.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
