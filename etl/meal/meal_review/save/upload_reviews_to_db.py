import sys
import argparse
import math
from pathlib import Path
from typing import Dict, List, Final, Optional

import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
from psycopg2.extensions import connection, cursor

# 상위 디렉토리의 유틸리티 및 상수 임포트
CURRENT_DIR: Final[Path] = Path(__file__).resolve().parent
PROJECT_ROOT: Final[Path] = CURRENT_DIR.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from common_utils import (
    logger,
    get_project_root
)

# -----------------------------------------------------------------------
# [수정] upload_to_db.py 와 동일한 bigint out of range 버그가 존재하여
# NaN / None / 범위 초과값을 안전하게 처리하는 헬퍼 함수를 동일하게 추가.
# psycopg2는 Python int를 bigint로 전송하는데 DB 컬럼이 INT(±21억) 이므로
# 범위를 초과하거나 NaN이 들어오면 OperationalError 가 발생한다.
# -----------------------------------------------------------------------
_INT_MAX: Final[int] = 2_147_483_647
_INT_MIN: Final[int] = -2_147_483_648


def _safe_int(value: object, default: int = 0) -> int:
    """NaN / None / 범위 초과값을 INT로 안전하게 변환합니다."""
    try:
        if value is None or (isinstance(value, float) and math.isnan(value)):
            return default
        converted = int(float(str(value)))
        return max(_INT_MIN, min(_INT_MAX, converted))
    except (ValueError, TypeError):
        return default


def _safe_float(value: object, default: float = 0.0) -> float:
    """NaN / None 값을 float 로 안전하게 변환합니다."""
    try:
        if value is None or (isinstance(value, float) and math.isnan(value)):
            return default
        return float(str(value))
    except (ValueError, TypeError):
        return default


def _safe_bigint(value: object) -> Optional[int]:
    """map_id 등 BIGINT FK 컬럼 — NaN 이면 None(NULL) 을 반환합니다."""
    try:
        if value is None or (isinstance(value, float) and math.isnan(value)):
            return None
        return int(float(str(value)))
    except (ValueError, TypeError):
        return None

def upload_reviews_to_crawling(df: pd.DataFrame, conn_args: Dict[str, str], truncate_review_only: bool) -> None:
    """
    클렌징된 리뷰 데이터를 crawling 테이블에 업로드합니다.
    """
    if df.empty:
        logger.warning("💡 업로드할 리뷰 데이터가 없습니다.")
        return

    conn: connection = psycopg2.connect(**conn_args)
    try:
        with conn:
            with conn.cursor() as cur:
                cur: cursor = cur
                if truncate_review_only:
                    logger.info("🧹 crawling 테이블 내 리뷰 데이터 초기화 중...")
                    cur.execute("DELETE FROM crawling WHERE thread = 'review'")
                
                columns: List[str] = [
                    "title", "content", "thread", "article_url", "created_at",
                    "view_count", "comment_count", "point", "author", "map_id", "category_cd"
                ]
                query: str = f"INSERT INTO crawling ({', '.join(columns)}) VALUES %s"
                
                # [수정] 기존 raw int()/float() 직접 변환은 NaN이나 범위 초과 시
                # psycopg2.errors.NumericValueOutOfRange 를 발생시킴.
                # 안전 변환 함수로 교체하여 동일 오류 방지.
                values: List[tuple] = [
                    (
                        str(r["title"]),
                        str(r["content"]),
                        str(r["thread"]),
                        str(r["article_url"]),
                        r["created_at"],
                        _safe_int(r["view_count"]),
                        _safe_int(r["comment_count"]),
                        _safe_float(r["point"]),
                        str(r["author"]),
                        _safe_bigint(r["map_id"]),
                        # [수정] category_cd 가 None 이면 str(None)='None' 이 아닌
                        # 실제 NULL로 넘겨야 DB FK 오류가 발생하지 않음
                        None if (r["category_cd"] is None or str(r["category_cd"]) in ("", "None", "nan")) else str(r["category_cd"])
                    )
                    for r in df.to_dict("records")
                ]
                
                execute_values(cur, query, values)
                logger.info(f"✅ {len(df)}건의 리뷰 데이터가 crawling 테이블에 적재되었습니다.")
    except Exception as e:
        logger.error(f"❌ 리뷰 DB 적재 실패: {str(e)}")
        raise
    finally:
        conn.close()

def main() -> None:
    parser = argparse.ArgumentParser(description="[Next-Gen] 리뷰 데이터 DB 적재 (Save)")
    
    parser.add_argument("--input", required=True, help="cleansing 단계에서 생성된 리뷰 CSV")
    parser.add_argument("--host", required=True)
    parser.add_argument("--port", type=int, default=5432)
    parser.add_argument("--dbname", required=True)
    parser.add_argument("--user", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--truncate-reviews", action="store_true")
    
    args = parser.parse_args()

    # 1. 데이터 로드
    logger.info(f"📥 리뷰 데이터 로드 중: {args.input}")
    try:
        df_cleansed: pd.DataFrame = pd.read_csv(args.input)
    except Exception as e:
        logger.error(f"리뷰 데이터 로드 실패: {str(e)}")
        return

    # 2. DB 업로드
    conn_args: Dict[str, str] = {
        "host": args.host, "port": str(args.port), "dbname": args.dbname,
        "user": args.user, "password": args.password
    }
    upload_reviews_to_crawling(df_cleansed, conn_args, args.truncate_reviews)

if __name__ == "__main__":
    main()
