import argparse
import glob
import json
import os
from pathlib import Path
from typing import Dict, List

import pandas as pd
import psycopg2
from psycopg2.extras import execute_values



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

def cleanup_files(json_dir: str, intermediate_csv: str) -> None:
    try:
        json_paths = glob.glob(os.path.join(json_dir, "*.json"))
        for path in json_paths:
            os.remove(path)
        if os.path.exists(intermediate_csv):
            os.remove(intermediate_csv)
        print("✅ 성공적으로 임시 파일들(JSON, CSV)이 삭제되었습니다.")
    except Exception as e:
        print(f"❌ 임시 파일 삭제 실패: {e}")

def get_or_create_crawler_user(cur) -> int:
    # Check if we have crawler bot
    cur.execute("SELECT user_id FROM users WHERE google_id = 'crawler_bot'")
    row = cur.fetchone()
    if row:
        return row[0]
    # In case not, create one
    cur.execute("""
        INSERT INTO users (email, nickname, google_id, status_cd)
        VALUES ('crawler@sk.com', 'Data Crawler', 'crawler_bot', 'ST01')
        RETURNING user_id
    """)
    return cur.fetchone()[0]

def upload_reviews(df: pd.DataFrame, conn_args: Dict[str, str], truncate_first: bool) -> None:
    if df.empty:
        print("업로드할 리뷰 데이터가 없습니다.")
        return
        
    conn = psycopg2.connect(**conn_args)
    try:
        with conn:
            with conn.cursor() as cur:
                if truncate_first:
                    # Truncate posts conditionally? We may not want to truncate ALL posts as they include user data.
                    # We will comment this out to protect other posts.
                    # cur.execute("TRUNCATE TABLE posts RESTART IDENTITY CASCADE")
                    pass

                user_id = get_or_create_crawler_user(cur)

                # shop_id, map_id 맵핑 조회
                cur.execute("""
                    SELECT m.name, m.address_detail, s.shop_id, s.map_id 
                    FROM shop s 
                    JOIN maps m ON s.map_id = m.map_id
                """)
                rows = cur.fetchall()
                
                # 공백을 제거한 키를 사용하여 맵핑의 안정성을 높입니다.
                shop_id_lookup = {}
                for name_db, addr_db, shop_id, map_id in rows:
                    if name_db and addr_db:
                        k1 = str(name_db).replace(" ", "")
                        k2 = str(addr_db).replace(" ", "")
                        shop_id_lookup[(k1, k2)] = (shop_id, map_id)

                review_values = []
                missing_shop_ids_count = 0
                
                for row in df.to_dict("records"):
                    n = str(row.get("store_name", "")).replace(" ", "")
                    a = str(row.get("store_address", "")).replace(" ", "")
                    
                miss_count = 0
                inserted_posts = 0
                inserted_images = 0
                from datetime import datetime

                for row in df.to_dict("records"):
                    n = str(row.get("store_name", "")).replace(" ", "")
                    a = str(row.get("store_address", "")).replace(" ", "")
                    
                    mapping = shop_id_lookup.get((n, a))
                    if mapping is None:
                        miss_count += 1
                        continue
                    
                    shop_id, map_id = mapping
                    
                    rating_val = row.get("rating")
                    rating_str = f"{rating_val:.1f}" if pd.notna(rating_val) else "N/A"
                    keywords = row.get("keywords", "")
                    content = f"[평점: {rating_str}점]\n{row.get('content', '')}\n\n(키워드: {keywords})"
                    
                    title = f"{row.get('store_name', '')} 리뷰"
                    if len(title) > 100:
                        title = title[:97] + "..."
                        
                    date_val = row.get("date")
                    try:
                        dt = datetime.strptime(str(date_val), "%Y-%m-%d")
                    except Exception:
                        dt = datetime.now()

                    cur.execute("""
                        INSERT INTO posts (title, content, created_at, modify_at, status_cd, post_cd, user_id, map_id, shop_id, crawling_id)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NULL)
                        RETURNING post_id
                    """, (title, content, dt, dt, 'ST01', 'PT03', user_id, map_id, shop_id))
                    
                    post_id = cur.fetchone()[0]
                    inserted_posts += 1

                    img_paths_val = row.get("image_paths", "")
                    if img_paths_val:
                        img_paths = [p.strip() for p in str(img_paths_val).split(",") if p.strip()]
                        for img in img_paths:
                            cur.execute("""
                                INSERT INTO images (image_url, table_name, table_id)
                                VALUES (%s, %s, %s)
                            """, (img, 'posts', post_id))
                            inserted_images += 1

                print(f"✅ 성공적으로 {inserted_posts}개의 리뷰와 {inserted_images}개의 이미지를 DB에 삽입했습니다.")
                
                if miss_count > 0:
                    print(f"⚠️ 경고: DB (shop/maps 테이블)에서 가게 정보를 찾지 못해 스킵된 리뷰 {miss_count}개 존재")
                    
    finally:
        conn.close()

def main() -> None:
    parser = argparse.ArgumentParser(description="맛집 리뷰 JSON을 파싱 후 PostgreSQL에 업로드")
    BASE_DIR = Path(__file__).resolve().parent.parent
    parser.add_argument("--json-dir", default=str(BASE_DIR / "review_data" / "jsons"), help="리뷰 JSON 폴더")
    parser.add_argument("--raw-csv", default=str(BASE_DIR / "data" / "raw_store_data.csv"), help="store_url -> 주소 맵핑용 CSV 파일")
    parser.add_argument("--output-dir", default=str(BASE_DIR / "review_data"), help="중간 산출물(review.csv) 저장 폴더")
    
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
    try:
        upload_reviews(df, conn_args, args.truncate_first)
        print("✅ 리뷰 DB 처리 완료.")
        cleanup_files(args.json_dir, str(Path(args.output_dir) / "review.csv"))
    except Exception as e:
        print(f"❌ 리뷰 DB 업로드 실패: {e}")
        raise

if __name__ == "__main__":
    main()
