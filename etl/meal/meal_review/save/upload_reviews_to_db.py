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
    get_project_root,
    get_hive_path
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
    클렌징된 리뷰 데이터를 crawling 테이블에 업로드하고, 이미지 정보를 images 테이블에 적재합니다.
    AWS 호환성을 위해 적재 성공 내역을 Hive 스타일(save/review)로 저장합니다.
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
                    logger.info("🧹 crawling 및 images 테이블 내 리뷰 데이터 초기화 중...")
                    # thread='review'인 항목들만 삭제하여 기존 가게 데이터(thread='shop')는 유지
                    cur.execute("DELETE FROM crawling WHERE thread = 'review'")
                
                success_count = 0
                for _, r in df.iterrows():
                    # [추가] map_id 조회 로직
                    # crawling 테이블에서 thread='shop' 이고 article_url 이 동일한 항목의 map_id 를 가져와 연결합니다.
                    article_url = str(r.get("article_url", ""))
                    cur.execute("SELECT map_id FROM crawling WHERE thread = 'shop' AND article_url = %s", (article_url,))
                    row = cur.fetchone()
                    map_id = row[0] if row else _safe_bigint(r.get("map_id"))

                    # 1. crawling 테이블 INSERT
                    columns = [
                        "title", "content", "thread", "article_url", "created_at",
                        "view_count", "comment_count", "point", "author", "map_id", "category_cd"
                    ]
                    query = f"INSERT INTO crawling ({', '.join(columns)}) VALUES %s RETURNING crawling_id"
                    
                    category_cd = None if (r["category_cd"] is None or str(r["category_cd"]) in ("", "None", "nan")) else str(r["category_cd"])
                    val = (
                        str(r["title"]), str(r["content"]), "review", article_url, r["created_at"],
                        _safe_int(r["view_count"]), _safe_int(r["comment_count"]), _safe_float(r["point"]),
                        str(r["author"]), map_id, category_cd
                    )
                    
                    cur.execute(query, [val])
                    crawling_id = cur.fetchone()[0]

                    # 2. images 테이블 INSERT (리뷰 이미지 경로 적재)
                    try:
                        import json
                        # [수정] images 테이블 스키마 매핑 (image_url, table_name, table_id)
                        local_paths: List[str] = json.loads(str(r.get("local_image_paths", "[]")))
                        for path in local_paths:
                            cur.execute(
                                "INSERT INTO images (image_url, table_name, table_id) VALUES (%s, %s, %s)",
                                (path, "crawling", crawling_id)
                            )
                    except Exception as img_e:
                        logger.warning(f"⚠️ 이미지 DB 적재 실패: {img_e}")

                    success_count += 1

                # [추가] DB 적재 성공 내역을 Hive 스타일 데이터 레이크(save/review)에 저장 (AWS 감사 로그용)
                if success_count > 0:
                    save_path: Path = get_hive_path("process=save", "service=review", "success")
                    df.to_csv(save_path, index=False, encoding="utf-8-sig")
                    logger.info(f"📂 리뷰 적재 내역 저장 완료(save/review): {save_path.name}")
                    
                logger.info(f"✅ {success_count}건의 리뷰 데이터 및 이미지가 적재되었습니다.")
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
