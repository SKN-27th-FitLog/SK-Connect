import sys
import argparse
from pathlib import Path
from typing import Dict, List, Final, Optional
from datetime import datetime

import pandas as pd

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
from members import Category

# crawling 테이블의 category_cd: 리뷰는 맛집(음식) 카테고리(CA01)로 고정.
# None 또는 빈 문자열로 저장하면 upload_reviews_to_db.py 에서
# str(None)='None' 으로 변환되어 codeT FK 오류가 발생할 수 있다.
DEFAULT_REVIEW_CATEGORY: str = Category.RESTAURANT.value  # "CA01"

def preprocess_reviews(df: pd.DataFrame) -> pd.DataFrame:
    """
    수집된 리뷰 데이터를 crawling 테이블 형식에 맞게 전처리합니다.
    """
    now: datetime = datetime.now()
    processed_records: List[Dict[str, object]] = []

    for _, row in df.iterrows():
        content_body: str = str(row.get("content", "")).strip()
        if not content_body:
            continue
            
        rating_val: float = float(pd.to_numeric(row.get("rating"), errors="coerce") or 0.0)
        store_name: str = str(row.get("store_name", "식당"))
        
            # crawling 테이블 스키마 매핑
            record: Dict[str, object] = {
                "title": f"{store_name} 리뷰",
                "content": content_body,
                "thread": "review",
                "article_url": str(row.get("store_url", "")),
                "created_at": str(row.get("date")) if pd.notna(row.get("date")) else now,
                "view_count": 0,
                "comment_count": 0,
                "point": rating_val,
                "author": "crawler_bot",
                "map_id": None,
                # [추가] 이미지 경로 데이터 보존 (upload 단계에서 사용)
                "local_image_paths": row.get("local_image_paths", "[]"),
                # 맛집 추천 서비스 특성상 CA01(맛집)을 기본 카테고리로 사용.
                "category_cd": DEFAULT_REVIEW_CATEGORY
            }
        processed_records.append(record)
        
    return pd.DataFrame(processed_records)

def main() -> None:
    parser = argparse.ArgumentParser(description="[Next-Gen] 리뷰 데이터 전처리 (Cleaning)")
    parser.add_argument("--input", required=True, help="raw 단계 수집 리뷰 CSV")
    args = parser.parse_args()

    logger.info(f"🔄 리뷰 전처리 시작: {args.input}")
    try:
        df_raw: pd.DataFrame = pd.read_csv(args.input)
        df_cleaned: pd.DataFrame = preprocess_reviews(df_raw)
        
        if not df_cleaned.empty:
            # [수정] 클렌징된 리뷰 데이터를 Hive 스타일 데이터 레이크(cleansing/review)에 저장합니다.
            # AWS S3 데이터 레이크와의 규약을 맞추기 위해 하이브 파티션 구조를 유지합니다.
            save_path: Path = get_hive_path("process=cleansing", "service=review", "success")
            df_cleaned.to_csv(save_path, index=False, encoding="utf-8-sig")
            logger.info(f"📂 클렌징 리뷰 저장 완료(cleansing/review): {save_path.name}")
        else:
            logger.warning("처리할 유효 리뷰 데이터가 없습니다.")
            
    except Exception as e:
        logger.error(f"전처리 중 오류 발생: {str(e)}")
        raise

if __name__ == "__main__":
    main()
