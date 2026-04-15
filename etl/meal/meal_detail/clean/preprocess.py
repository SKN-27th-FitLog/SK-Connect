import sys
import argparse
import os
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Final
from datetime import datetime

import pandas as pd

# 상위 디렉토리의 유틸리티 및 상수 임포트
CURRENT_DIR: Final[Path] = Path(__file__).resolve().parent
PROJECT_ROOT: Final[Path] = CURRENT_DIR.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from common_utils import (
    logger,
    normalize_string, 
    get_hive_path,
    get_project_root
)
from members import FoodCategory, Location

def load_code_tables(code_csv: str) -> Tuple[Dict[str, str], Dict[str, str]]:
    """
    공통 코드 테이블(codeT)을 로드하여 카테고리 및 지역 매핑 딕셔너리를 반환합니다.
    """
    try:
        df_cd: pd.DataFrame = pd.read_csv(code_csv)
        # FC(음식분류) 또는 CA(카테고리)로 시작하는 코드 매핑
        category_map: Dict[str, str] = {
            str(row["name"]).strip(): str(row["cd"]).strip() 
            for _, row in df_cd.iterrows() 
            if str(row["cd"]).strip().startswith(("FC", "CA"))
        }
        # LA00(기본 지역) 하위의 지역 코드 매핑
        address_map: Dict[str, str] = {
            str(row["name"]).strip(): str(row["cd"]).strip() 
            for _, row in df_cd.iterrows() 
            if str(row["cd_upper"]).strip() == Location.DEFAULT.value
        }
        return category_map, address_map
    except Exception as e:
        logger.error(f"⚠️ 코드 테이블 로드 실패: {str(e)}")
        return {}, {}

def transform_to_crawling_format(raw_csv: str, code_csv: str, default_cat: str) -> pd.DataFrame:
    """
    원본 CSV 데이터를 crawling 테이블 스키마에 맞게 변환합니다.
    """
    category_map, _ = load_code_tables(code_csv)
    
    df: pd.DataFrame = pd.read_csv(raw_csv)
    # 수집 성공 데이터만 필터링
    df = df[df["status"] == "ok"].copy()
    
    transformed_records: List[Dict[str, object]] = []
    now: datetime = datetime.now()
    
    for _, row in df.iterrows():
        store_name: str = str(row.get("store_name", "")).strip()
        if not store_name:
            continue
            
        # 카테고리 코드 결정
        src_cat: str = str(row.get("source_category", "")).strip()
        cat_cd: str = category_map.get(src_cat, default_cat)
        
        # crawling 테이블 매핑 (Any 사용 금지 원칙 준수)
        record: Dict[str, object] = {
            "title": store_name,
            "content": f"주소: {row.get('store_address', '')}\n메뉴: {row.get('menus_json', '[]')}",
            "thread": "shop",
            "article_url": str(row.get("store_url", "")),
            "created_at": now,
            "view_count": 0,
            "comment_count": 0,
            "point": float(pd.to_numeric(row.get("store_rating"), errors="coerce") or 0.0),
            "author": "crawler_bot",
            "map_id": None, 
            "category_cd": cat_cd
        }
        transformed_records.append(record)
        
    return pd.DataFrame(transformed_records)

def main() -> None:
    parser = argparse.ArgumentParser(description="[Next-Gen] 맛집 상세 정보 전처리 (Cleaning)")
    PROJECT_ROOT: Path = get_project_root()
    
    parser.add_argument("--input", required=True, help="raw 단계 수집 CSV 파일")
    # 코드 테이블 경로는 프로젝트 구조에 따라 유연하게 설정 (상대 경로 지양)
    # 예: PROJECT_ROOT / ".." / "database" / "data" / "codeT.csv"
    parser.add_argument("--code-table", required=True)
    parser.add_argument("--default-category-cd", default=FoodCategory.KOREAN.value)
    
    args = parser.parse_args()

    # 1. 데이터 변환
    logger.info(f"🔄 데이터 전처리 시작: {args.input}")
    df_transformed: pd.DataFrame = transform_to_crawling_format(
        args.input, args.code_table, args.default_category_cd
    )
    
    # 2. 데이터 레이크(process=cleansing/service=shop) 저장
    # AWS S3 데이터 레이크와의 규약을 맞추기 위해 하이브 파티션 구조를 유지합니다.
    if not df_transformed.empty:
        save_path: Path = get_hive_path("process=cleansing", "service=shop", "success")
        df_transformed.to_csv(save_path, index=False, encoding="utf-8-sig")
        logger.info(f"📂 클렌징 데이터 저장 완료(cleansing/shop): {save_path.name}")
    else:
        logger.warning("처리할 유효 데이터가 없습니다.")

if __name__ == "__main__":
    main()
