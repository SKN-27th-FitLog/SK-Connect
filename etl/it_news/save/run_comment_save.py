"""
comment save 스테이지 실행기.

comment cleaning 성공 파일을 읽어 comments 테이블에 적재하고,
이미 존재하는 댓글은 건너뛰어 중복 적재를 방지한다.
"""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

from common.settings import env, get_config
from common.runtime import (
    cleaning_success_files,
    connect,
    existing_comment_keys,
    filter_existing_comments,
    insert_comment_dataframe,
    log_path,
    make_stage_paths,
    source_csv_path,
)

######################
# 설정 기반 상수 관련
######################
CONFIG = get_config()
PATHS_CONFIG = CONFIG["paths"]
COMMENTS_CONFIG = CONFIG["comments"]
CSV_ENCODING = PATHS_CONFIG["csv_encoding"]
_KST = ZoneInfo(CONFIG["timezone"])


######################
# 실행 인자 및 실행 시각 처리 관련
######################
def parse_args() -> argparse.Namespace:
    """
    comment save 단계 실행 인자를 파싱한다.

    Returns:
        실행 날짜와 기본 사용자 ID 옵션이 담긴 argparse 네임스페이스.
    """
    parser = argparse.ArgumentParser(description="IT News comment save stage runner")
    parser.add_argument("--date", default=None, help="기본값은 오늘(KST), YYYY-MM-DD 형식")
    parser.add_argument("--user-id", type=int, default=None, help="comments.user_id 로 사용할 기본 사용자 ID")
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
# comment 저장 기본값 처리 관련
######################
def resolve_comment_user_id(arg_value: int | None) -> int:
    """
    comments.user_id 에 넣을 기본 사용자 ID를 CLI 또는 환경 변수에서 결정한다.

    Args:
        arg_value: CLI에서 받은 사용자 ID.

    Returns:
        실제 저장에 사용할 사용자 ID.
    """
    if arg_value is not None:
        return arg_value

    # user_id 환경변수 이름도 설정화해 환경마다 키를 바꿔도 코드를 수정하지 않게 한다.
    for env_key in COMMENTS_CONFIG["user_id_env_keys"]:
        raw = env(env_key, "")
        if raw not in (None, ""):
            return int(raw)
    raise SystemExit("comment save용 user_id가 없습니다. --user-id 또는 IT_NEWS_COMMENT_USER_ID를 설정하세요.")


def write_dataframe(path: Path, df: pd.DataFrame) -> None:
    """
    DataFrame을 UTF-8 BOM CSV로 저장한다.

    Args:
        path: 저장 대상 CSV 경로.
        df: 저장할 데이터프레임.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding=CSV_ENCODING)


######################
# comment save 실행 흐름 관련
######################
def main() -> int:
    """
    comment cleaning 성공 파일을 읽어 comments 테이블에 적재하고 결과 파일을 기록한다.

    Returns:
        정상 종료 시 0, DB 연결 실패 시 1.
    """
    # DB 중복 비교 키를 먼저 조회해 같은 댓글이 다시 들어가지 않도록 한다.
    args = parse_args()
    user_id = resolve_comment_user_id(args.user_id)
    run_at = parse_run_at(args.date)
    save_paths = make_stage_paths(PATHS_CONFIG["save_bucket"], run_at, kind=PATHS_CONFIG["comment_kind"])
    files = cleaning_success_files(run_at, kind=PATHS_CONFIG["comment_kind"])
    if not files:
        raise SystemExit("save 대상 comment cleaning 성공 파일이 없습니다.")

    try:
        conn = connect()
    except Exception as exc:
        print(f"DB 연결 실패: {exc}")
        return 1

    try:
        for file_path in files:
            df = pd.read_csv(file_path)
            success_path = source_csv_path(save_paths, file_path.name, ok=True)
            fail_path = source_csv_path(save_paths, file_path.name, ok=False)

            try:
                # crawling_id/created_at/content 조합이 이미 DB에 있으면 다시 넣지 않는다.
                crawling_ids = sorted({int(value) for value in df["crawling_id"].dropna().tolist()}) if not df.empty else []
                filtered = filter_existing_comments(df, existing_comment_keys(conn, crawling_ids))
                inserted = insert_comment_dataframe(conn, filtered, user_id=user_id)
                conn.commit()
                result_df = filtered.copy()
                if not result_df.empty:
                    result_df["user_id"] = user_id
                write_dataframe(success_path, result_df)
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
