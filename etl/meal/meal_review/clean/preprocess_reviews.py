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
    parser = argparse.ArgumentParser(description="리뷰 데이터 클렌징 및 스키마 변환")
    parser.add_argument("--input", required=True, help="원본 리뷰 CSV 경로")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        logger.error(f"입력 파일 없음: {input_path}")
        return

    try:
        df: pd.DataFrame = pd.read_csv(input_path)
        
        if df.empty:
            logger.warning(f"💡 입력 데이터가 비어 있습니다. 빈 결과를 생성합니다: {input_path.name}")
            processed_df = pd.DataFrame(columns=[
                "title", "content", "thread", "article_url", "created_at",
                "view_count", "comment_count", "point", "author", "map_id",
                "local_image_paths", "category_cd"
            ])
        else:
            processed_df = preprocess_reviews(df)
            
        save_path: Path = get_hive_path("process=cleansing", "service=review", "success")
        processed_df.to_csv(save_path, index=False, encoding="utf-8-sig")
        logger.info(f"✅ 리뷰 정제 완료. Hive 저장(cleansing/review): {save_path.name}")
        
    except pd.errors.EmptyDataError:
        logger.warning(f"⚠️ 빈 파일 감지 (EmptyDataError): {input_path.name}. 빈 결과물을 생성합니다.")
        save_path: Path = get_hive_path("process=cleansing", "service=review", "success")
        pd.DataFrame().to_csv(save_path, index=False, encoding="utf-8-sig")
    except Exception as e:
        logger.error(f"❌ 전처리 중 오류 발생: {str(e)}")

if __name__ == "__main__":
    main()
