import sys
import argparse
import math
from pathlib import Path
from typing import Dict, List, Final, Optional

import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
from psycopg2.extensions import connection, cursor

# PostgreSQL INT 범위 (view_count, comment_count)
_INT_MAX: Final[int] = 2_147_483_647
_INT_MIN: Final[int] = -2_147_483_648


def _safe_int(value: object, default: int = 0) -> int:
    """NaN / None / 범위 초과값을 안전하게 INT로 변환합니다."""
    try:
        if value is None or (isinstance(value, float) and math.isnan(value)):
            return default
        converted = int(float(str(value)))
        return max(_INT_MIN, min(_INT_MAX, converted))
    except (ValueError, TypeError):
        return default


def _safe_float(value: object, default: float = 0.0) -> float:
    """NaN / None 값을 안전하게 float로 변환합니다."""
    try:
        if value is None or (isinstance(value, float) and math.isnan(value)):
            return default
        return float(str(value))
    except (ValueError, TypeError):
        return default


def _safe_bigint(value: object) -> Optional[int]:
    """map_id 등 BIGINT FK 컬럼 — NaN이면 None(NULL) 반환합니다."""
    try:
        if value is None or (isinstance(value, float) and math.isnan(value)):
            return None
        return int(float(str(value)))
    except (ValueError, TypeError):
        return None

# 상위 디렉토리의 유틸리티 및 상수 임포트
CURRENT_DIR: Final[Path] = Path(__file__).resolve().parent
PROJECT_ROOT: Final[Path] = CURRENT_DIR.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from common_utils import (
    logger,
    get_hive_path,
    get_project_root
)

def upload_to_crawling(df: pd.DataFrame, conn_args: Dict[str, str], truncate_first: bool) -> None:
    """
    변환된 데이터를 데이터베이스의 crawling 테이블에 업로드합니다.
    (Any 사용 금지 원칙 준수를 위해 명시적 타입 지정)
    """
    if df.empty:
        logger.warning("💡 업로드할 데이터가 없습니다.")
        return

    conn: connection = psycopg2.connect(**conn_args)
    try:
        with conn:
            with conn.cursor() as cur:
                cur: cursor = cur # 타입 힌트 보정
                if truncate_first:
                    logger.info("🧹 crawling 테이블 초기화 중...")
                    cur.execute("TRUNCATE TABLE crawling RESTART IDENTITY")
                
                # 데이터 삽입 (psycopg2 execute_values 사용)
                columns: List[str] = [
                    "title", "content", "thread", "article_url", "created_at",
                    "view_count", "comment_count", "point", "author", "map_id", "category_cd"
                ]
                query: str = f"INSERT INTO crawling ({', '.join(columns)}) VALUES %s"
                
                # DataFrame 데이터를 튜플 리스트로 변환 (NaN / 범위 초과값 안전 처리)
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
                        str(r["category_cd"])
                    )
                    for r in df.to_dict("records")
                ]
                
                execute_values(cur, query, values)
                logger.info(f"✅ {len(df)}건의 데이터가 crawling 테이블에 최종 적재되었습니다.")
    except Exception as e:
        logger.error(f"❌ DB 적재 중 치명적 오류 발생: {str(e)}")
        raise
    finally:
        conn.close()

def main() -> None:
    parser = argparse.ArgumentParser(description="[Next-Gen] 맛집 데이터 DB 적재 (Save)")
    
    parser.add_argument("--input", required=True, help="cleansing 단계에서 생성된 CSV 파일")
    parser.add_argument("--host", required=True)
    parser.add_argument("--port", type=int, default=5432)
    parser.add_argument("--dbname", required=True)
    parser.add_argument("--user", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--truncate-first", action="store_true")
    
    args = parser.parse_args()

    # 1. 클렌징된 데이터 로드
    logger.info(f"📥 데이터 로드 중: {args.input}")
    try:
        df_cleansed: pd.DataFrame = pd.read_csv(args.input)
    except Exception as e:
        logger.error(f"데이터 로드 실패: {str(e)}")
        return

    # 2. DB 업로드
    conn_args: Dict[str, str] = {
        "host": args.host, "port": str(args.port), "dbname": args.dbname,
        "user": args.user, "password": args.password
    }
    upload_to_crawling(df_cleansed, conn_args, args.truncate_first)

if __name__ == "__main__":
    main()
