import argparse
import glob
import json
import os
from pathlib import Path
from typing import Dict, List

import pandas as pd
import psycopg2
from psycopg2.extras import execute_values

DDL = """
CREATE TABLE IF NOT EXISTS review (
  review_id BIGSERIAL PRIMARY KEY,
  shop_id BIGINT NOT NULL,
  source_review_id VARCHAR(50),
  rating FLOAT,
  date VARCHAR(30),
  content TEXT,
  keywords TEXT,
  image_paths TEXT
);
"""

def process_jsons_to_df(json_dir: str, raw_csv: str) -> pd.DataFrame:
    # 1. URL -> Address 맵핑 (raw_store_data.csv)
    url_to_addr = {}
    if os.path.exists(raw_csv):
        df_raw = pd.read_csv(raw_csv)
        for _, row in df_raw.iterrows():
            url = str(row.get("store_url", "")).strip()
            addr = str(row.get("store_address", "")).strip()
            if url and addr:
                url_to_addr[url] = addr

    records = []
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
                    img_str = ", ".join(rv.get("image_paths", []))
                    
                    records.append({
                        "store_name": store_name,
                        "store_url": store_url,
                        "store_address": store_address,
                        "source_review_id": rv.get("review_id", ""),
                        "rating": pd.to_numeric(rv.get("rating"), errors="coerce"),
                        "date": str(rv.get("date", "")).strip(),
                        "content": str(rv.get("content", "")).strip(),
                        "keywords": kw_str,
                        "image_paths": img_str,
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

def upload_reviews(df: pd.DataFrame, conn_args: Dict[str, str], truncate_first: bool) -> None:
    if df.empty:
        print("업로드할 리뷰 데이터가 없습니다.")
        return
        
    conn = psycopg2.connect(**conn_args)
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(DDL)
                if truncate_first:
                    cur.execute("TRUNCATE TABLE review RESTART IDENTITY CASCADE")

                # shop_id 맵핑 조회
                cur.execute("""
                    SELECT m.name, m.address_detail, s.shop_id 
                    FROM shop s 
                    JOIN maps m ON s.map_id = m.map_id
                """)
                rows = cur.fetchall()
                
                # 공백을 제거한 키를 사용하여 맵핑의 안정성을 높입니다.
                shop_id_lookup = {}
                for name_db, addr_db, shop_id in rows:
                    if name_db and addr_db:
                        k1 = str(name_db).replace(" ", "")
                        k2 = str(addr_db).replace(" ", "")
                        shop_id_lookup[(k1, k2)] = shop_id

                review_values = []
                missing_shop_ids_count = 0
                
                for row in df.to_dict("records"):
                    n = str(row.get("store_name", "")).replace(" ", "")
                    a = str(row.get("store_address", "")).replace(" ", "")
                    
                    shop_id = shop_id_lookup.get((n, a))
                    if shop_id is None:
                        missing_shop_ids_count += 1
                        continue
                        
                    rating = row.get("rating")
                    if pd.isna(rating):
                        rating = None
                        
                    review_values.append((
                        shop_id,
                        row.get("source_review_id"),
                        rating,
                        row.get("date"),
                        row.get("content"),
                        row.get("keywords"),
                        row.get("image_paths"),
                    ))

                if review_values:
                    execute_values(
                        cur, 
                        "INSERT INTO review (shop_id, source_review_id, rating, date, content, keywords, image_paths) VALUES %s", 
                        review_values
                    )
                    print(f"성공적으로 {len(review_values)}개의 리뷰를 DB에 삽입했습니다.")
                
                if missing_shop_ids_count > 0:
                    print(f"경고: DB (shop/maps 테이블)에서 가게 정보를 찾지 못해 스킵된 리뷰 {missing_shop_ids_count}개 존재")
                    
    finally:
        conn.close()

def main() -> None:
    parser = argparse.ArgumentParser(description="맛집 리뷰 JSON을 파싱 후 PostgreSQL에 업로드")
    parser.add_argument("--json-dir", default="../review_data/jsons", help="리뷰 JSON 폴더")
    parser.add_argument("--raw-csv", default="../data/raw_store_data.csv", help="store_url -> 주소 맵핑용 CSV 파일")
    parser.add_argument("--output-dir", default="../review_data", help="중간 산출물(review.csv) 저장 폴더")
    
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
    
    print("DB 업로드 시작...")
    upload_reviews(df, conn_args, args.truncate_first)


if __name__ == "__main__":
    main()
