import sys
import argparse
import glob
import json
import os
import re
import shutil
import hashlib
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Set
from datetime import datetime

import pandas as pd
import psycopg2
from psycopg2.extras import execute_values

# 상위 디렉토리(c:\dev\Study\meal\)의 common_utils 임포트 지원
CURRENT_DIR = Path(__file__).resolve().parent
PARENT_DIR = CURRENT_DIR.parent
if str(PARENT_DIR) not in sys.path:
    sys.path.append(str(PARENT_DIR))

try:
    from common_utils import (
        normalize_string, 
        fetch_coordinates_kakao, 
        archive_files,
        safe_re_sub_space,
        generate_content_hash,
        get_or_create_crawler_user
    )
    from members import Status, PostType, TablePrefix
except ImportError:
    # 예외 상황용 로컬 정의 (폴백)
    def normalize_string(text: str) -> str: return str(text).lower()
    def get_or_create_crawler_user(cur): return 1
    class Status: ACTIVE = "ST01"
    class PostType: OPERATIONAL = "PT03"
    class TablePrefix: TABLE = "TC00"

# 전역 설정: 테이블별 PK 명칭 정의
TABLE_PK_MAP = {
    "posts": "post_id",
    "maps": "map_id",
    "shop": "shop_id",
    "crawling": "crawling_id"
}

def process_jsons_to_df(json_dir: str, raw_csv: str) -> pd.DataFrame:
    # 1. URL -> Address 맵핑 (raw_store_data.csv)
    url_to_addr: Dict[str, str] = {}
    if os.path.exists(raw_csv):
        df_raw = pd.read_csv(raw_csv)
        for _, row in df_raw.iterrows():
            url = str(row.get("store_url", "")).strip()
            addr = str(row.get("store_address", "")).strip()
            if url and addr:
                url_to_addr[url] = addr

    records: List[Dict] = []
    json_paths = glob.glob(os.path.join(json_dir, "*.json"))
    
    for path in json_paths:
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                store_url = data.get("store_url", "").strip()
                store_name = data.get("store_name", "").strip()
                store_address = url_to_addr.get(store_url, "")
                
                reviews = data.get("reviews", [])
                for rv in reviews:
                    kw_str = ", ".join(rv.get("keywords", []))
                    # 원본 URL 우선 사용, 없을 경우 로컬 경로 사용
                    img_urls = rv.get("image_urls", [])
                    if not img_urls:
                        img_urls = rv.get("image_paths", [])
                    
                    img_str = ", ".join(img_urls)
                    
                    records.append({
                        "store_name": store_name,
                        "store_url": store_url,
                        "store_address": store_address,
                        "source_review_id": rv.get("review_id", ""),
                        "rating": pd.to_numeric(rv.get("rating"), errors="coerce"),
                        "date": str(rv.get("date", "")).strip(),
                        "content": str(rv.get("content", "")).strip(),
                        "keywords": kw_str,
                        "image_urls": img_str,
                    })
        except Exception as e:
            print(f"Error parsing {path}: {e}")
            
    df = pd.DataFrame(records)
    return df

def save_intermediate(df: pd.DataFrame, out_dir: str) -> None:
    path = Path(out_dir)
    path.mkdir(parents=True, exist_ok=True)
    if not df.empty:
        df.to_csv(path / "review.csv", index=False, encoding="utf-8-sig")

def validate_image_mapping(cur, table_name: str, table_id: int, allowed_tables: Set[str]) -> bool:
    """이미지 매핑의 무결성을 검증합니다."""
    if table_name not in allowed_tables:
        return False
        
    pk_col = TABLE_PK_MAP.get(table_name)
    if not pk_col:
        return False
        
    # 대상 테이블에 실제 ID가 존재하는지 확인 (Batch 성능 고려 차후 최적화 가능)
    cur.execute(f"SELECT 1 FROM {table_name} WHERE {pk_col} = %s", (table_id,))
    return cur.fetchone() is not None

def upload_reviews(df: pd.DataFrame, conn_args: Dict[str, str], truncate_first: bool) -> None:
    if df.empty:
        print("업로드할 리뷰 데이터가 없습니다.")
        return
        
    conn = psycopg2.connect(**conn_args)
    try:
        with conn: # 전역 트랜잭션 시작
            with conn.cursor() as cur:
                # 1. crawler_bot 사용자 확보
                user_id = get_or_create_crawler_user(cur)

                # 2. 허용된 테이블 목록 (codeT 기반) 확보
                cur.execute("SELECT name FROM \"codeT\" WHERE cd_upper = %s OR cd LIKE 'TC%'", (TablePrefix.TABLE.value,))
                allowed_tables: Set[str] = {str(r[0]).strip().lower() for r in cur.fetchall()}
                if not allowed_tables: # 기본값 설정
                    allowed_tables = {"posts", "shop", "maps", "crawling"}

                # 3. shop_id, map_id 맵핑 조회 최적화
                cur.execute("""
                    SELECT m.name, m.address_detail, s.shop_id, s.map_id 
                    FROM shop s 
                    JOIN maps m ON s.map_id = m.map_id
                """)
                shop_id_lookup: Dict[Tuple[str, str], Tuple[int, int]] = {}
                for name_db, addr_db, sid, mid in cur.fetchall():
                    if name_db and addr_db:
                        # 정규화된 키로 맵핑
                        k1 = re.sub(r'\s+', '', str(name_db))
                        k2 = re.sub(r'\s+', '', str(addr_db))
                        shop_id_lookup[(k1, k2)] = (sid, mid)

                # 4. 리뷰 및 이미지 삽입
                inserted_posts = 0
                inserted_images = 0
                skipped_duplicates = 0

                for row in df.to_dict("records"):
                    content_body = str(row.get("content", "")).strip()
                    if not content_body:
                        continue
                        
                    # 본문 해시 체크 (중복 방지)
                    content_hash = generate_content_hash(content_body)
                    # 현재 posts 테이블에 content_hash 컬럼이 없으므로 내용 기반 조회 (성능상 한계가 있을 수 있음)
                    cur.execute("SELECT 1 FROM posts WHERE content LIKE %s LIMIT 1", (f"%{content_body[:200]}%",))
                    if cur.fetchone():
                        skipped_duplicates += 1
                        continue

                    n = re.sub(r'\s+', '', str(row.get("store_name", "")))
                    a = re.sub(r'\s+', '', str(row.get("store_address", "")))
                    
                    mapping = shop_id_lookup.get((n, a))
                    if mapping is None:
                        continue
                    
                    shop_id, map_id = mapping
                    rating_val = row.get("rating")
                    rating_str = f"{rating_val:.1f}" if pd.notna(rating_val) else "N/A"
                    keywords = row.get("keywords", "")
                    content = f"[평점: {rating_str}점]\n{content_body}\n\n(키워드: {keywords})"
                    
                    title = f"{row.get('store_name', '')} 리뷰"
                    if len(title) > 100:
                        title = title[:97] + "..."
                        
                    try:
                        dt = datetime.strptime(str(row.get("date")), "%Y-%m-%d")
                    except Exception:
                        dt = datetime.now()

                    cur.execute("""
                        INSERT INTO posts (title, content, created_at, modify_at, status_cd, post_cd, user_id, map_id, shop_id, crawling_id)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NULL)
                        RETURNING post_id
                    """, (title, content, dt, dt, Status.ACTIVE.value, PostType.OPERATIONAL.value, user_id, map_id, shop_id))
                    
                    post_id = cur.fetchone()[0]
                    inserted_posts += 1

                    # 이미지 삽입 (무결성 검증 포함)
                    img_urls_val = row.get("image_urls", "")
                    if img_urls_val:
                        urls = [u.strip() for u in str(img_urls_val).split(",") if u.strip()]
                        for url in urls:
                            if validate_image_mapping(cur, "posts", post_id, allowed_tables):
                                cur.execute("""
                                    INSERT INTO images (image_url, table_name, table_id)
                                    VALUES (%s, %s, %s)
                                """, (url, 'posts', post_id))
                                inserted_images += 1

                print(f"✅ 결과: 성공({inserted_posts}건), 이미지({inserted_images}건), 중복건너뜀({skipped_duplicates}건)")
                    
    finally:
        conn.close()

def main() -> None:
    parser = argparse.ArgumentParser(description="맛집 리뷰 JSON을 파싱 후 PostgreSQL에 업로드")
    BASE_DIR = Path(__file__).resolve().parent.parent
    parser.add_argument("--json-dir", default=str(BASE_DIR / "review_data" / "jsons"), help="리뷰 JSON 폴더")
    parser.add_argument("--raw-csv", default=str(BASE_DIR / "data" / "raw_store_data.csv"), help="store_url -> 주소 맵핑용 CSV 파일")
    parser.add_argument("--output-dir", default=str(BASE_DIR / "review_data"), help="중간 산출물(review.csv) 저장 폴더")
    parser.add_argument("--archive-dir", default=str(BASE_DIR / "review_data" / "archives"), help="아카이브 저장 폴더")
    
    parser.add_argument("--host", required=True)
    parser.add_argument("--port", type=int, default=5432)
    parser.add_argument("--dbname", required=True)
    parser.add_argument("--user", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--truncate-first", action="store_true")
    
    args = parser.parse_args()

    df = process_jsons_to_df(args.json_dir, args.raw_csv)
    print(f"총 {len(df)}건의 리뷰를 파싱 완료했습니다.")
    
    save_intermediate(df, args.output_dir)
    print(f"중간 파일 저장 완료: {Path(args.output_dir) / 'review.csv'}")

    conn_args = {
        "host": args.host,
        "port": args.port,
        "dbname": args.dbname,
        "user": args.user,
        "password": args.password,
    }
    
    print("DB 업로드 시작 (트랜잭션 강화 모드)...")
    try:
        upload_reviews(df, conn_args, args.truncate_first)
        print("✅ 리뷰 및 이미지 통합 처리 완료.")
        # 성공 시 아카이빙
        json_files = glob.glob(os.path.join(args.json_dir, "*.json"))
        archive_files(json_files + [str(Path(args.output_dir) / "review.csv")], args.archive_dir)
    except Exception as e:
        print(f"❌ 리뷰 DB 업로드 실패 (롤백됨): {e}")
        raise

if __name__ == "__main__":
    main()
