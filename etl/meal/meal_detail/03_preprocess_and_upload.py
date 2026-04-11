import sys
import os
import requests
import argparse
import json
import re
import shutil
from pathlib import Path
from typing import Dict, List, Tuple, Optional

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
        safe_re_sub_space
    )
    from members import Category, FoodCategory, Location
except ImportError:
    # 예외 상황용 로컬 정의 (폴백)
    def normalize_string(text: str) -> str: return str(text).lower()
    def fetch_coordinates_kakao(address: str, api_key: str): return 0.0, 0.0
    def archive_files(files, archive_dir): pass
    class Category: RESTAURANT = "CA01"
    class FoodCategory: KOREAN = "FC01"
    class Location: DEFAULT = "LA00"

# Constants
MAPS_COLUMNS = ["name", "category_cd", "address_cd", "address_detail", "latitude", "longitude"]
SHOP_COLUMNS = ["map_id", "category_cd", "rating"]
MENU_COLUMNS = ["shop_id", "name", "price"]

def load_code_tables(code_csv: str) -> Tuple[Dict[str, str], Dict[str, str]]:
    df_cd = pd.read_csv(code_csv)
    category_map = {str(row["name"]).strip(): str(row["cd"]).strip() for _, row in df_cd.iterrows() if str(row["cd"]).strip().startswith(("FC", "CA"))}
    address_map = {str(row["name"]).strip(): str(row["cd"]).strip() for _, row in df_cd.iterrows() if str(row["cd_upper"]).strip() == Location.DEFAULT.value}
    return category_map, address_map

def load_and_transform(raw_csv: str, code_csv: str, default_category_cd: str, default_address_cd: str) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    category_map, address_map = load_code_tables(code_csv)
    df = pd.read_csv(raw_csv)
    df = df[df["status"] == "ok"].copy()
    df["store_name"] = df["store_name"].fillna("").astype(str).str.strip()
    df["store_address"] = df["store_address"].fillna("").astype(str).str.strip()
    df = df[(df["store_name"] != "") & (df["store_address"] != "")].copy()

    # 초기 좌표값 설정
    df["latitude"] = 0.0
    df["longitude"] = 0.0
    
    def get_cat_cd(c) -> str:
        if pd.isna(c) or c == "":
            return default_category_cd
        return category_map.get(str(c).strip(), default_category_cd)

    def get_addr_info(a) -> Tuple[str, str]:
        a_str = str(a).strip()
        for key in sorted(address_map.keys(), key=len, reverse=True):
            if a_str.startswith(key):
                return address_map[key], a_str[len(key):].strip()
        return default_address_cd, a_str

    df["shop_category_cd"] = df["source_category"].apply(get_cat_cd) if "source_category" in df.columns else default_category_cd
    df["category_cd"] = Category.RESTAURANT.value
        
    if df.empty:
        df["address_cd"] = pd.Series(dtype=str)
    else:
        df["address_cd"], df["store_address"] = zip(*df["store_address"].apply(get_addr_info))

    maps_df = (
        df[["store_name", "category_cd", "address_cd", "store_address", "latitude", "longitude"]]
        .drop_duplicates()
        .rename(columns={"store_name": "name", "store_address": "address_detail"})
        .reset_index(drop=True)
    )

    shop_df = (
        df[["store_name", "store_address", "shop_category_cd", "store_rating"]]
        .drop_duplicates()
        .rename(columns={"store_rating": "rating", "shop_category_cd": "category_cd"})
        .reset_index(drop=True)
    )
    shop_df["rating"] = pd.to_numeric(shop_df["rating"], errors="coerce")

    menu_rows: List[Dict] = []
    for _, row in df.iterrows():
        try:
            menus = json.loads(row.get("menus_json", "[]") or "[]")
        except Exception:
            menus = []
        for menu in menus:
            menu_rows.append(
                {
                    "store_name": row["store_name"],
                    "store_address": row["store_address"],
                    "name": str(menu.get("menu_name", "")).strip(),
                    "price": pd.to_numeric(menu.get("menu_price"), errors="coerce"),
                }
            )
    menu_df = pd.DataFrame(menu_rows).drop_duplicates().reset_index(drop=True)
    return maps_df, shop_df, menu_df

def save_intermediate(maps_df: pd.DataFrame, shop_df: pd.DataFrame, menu_df: pd.DataFrame, out_dir: str) -> None:
    path = Path(out_dir)
    path.mkdir(parents=True, exist_ok=True)
    maps_df.to_csv(path / "maps.csv", index=False, encoding="utf-8-sig")
    shop_df.to_csv(path / "shop.csv", index=False, encoding="utf-8-sig")
    menu_df.to_csv(path / "menu.csv", index=False, encoding="utf-8-sig")

def get_existing_map_id(cur, name: str, address_detail: str, lat: float, lng: float) -> Optional[int]:
    """이름, 주소(정규화 비교) 또는 좌표(10m 이내) 기반으로 기존 map_id를 찾습니다."""
    norm_name = normalize_string(name)
    norm_addr = normalize_string(address_detail)
    
    # 1. 정규화된 이름과 주소로 먼저 검색
    cur.execute("SELECT map_id, name, address_detail, latitude, longitude FROM maps")
    rows = cur.fetchall()
    
    for mid, mname, maddr, mlat, mlng in rows:
        if normalize_string(mname) == norm_name and normalize_string(maddr) == norm_addr:
            return mid
        
        # 2. 좌표가 근접한지 확인 (간단한 거리 계산: 약 10m는 좌표 소수점 약 0.0001 차이)
        if lat != 0.0 and lng != 0.0 and mlat != 0.0 and mlng != 0.0:
            dist = ((lat - mlat)**2 + (lng - mlng)**2)**0.5
            if dist < 0.0001: # 약 10~11미터 수준
                return mid
    
    return None

def upload(maps_df: pd.DataFrame, shop_df: pd.DataFrame, menu_df: pd.DataFrame, conn_args: Dict[str, str], truncate_first: bool, kakao_api_key: str = "") -> None:
    conn = psycopg2.connect(**conn_args)
    try:
        with conn: # 트랜잭션 시작 (maps, shop, menu 전체 포함)
            with conn.cursor() as cur:
                if truncate_first:
                    cur.execute("TRUNCATE TABLE menu, shop, maps RESTART IDENTITY CASCADE")

                map_id_lookup: Dict[Tuple[str, str], int] = {}
                for row in maps_df.to_dict("records"):
                    lat, lng = row["latitude"], row["longitude"]
                    if lat == 0.0 and lng == 0.0 and kakao_api_key:
                        lat, lng = fetch_coordinates_kakao(row["address_detail"], kakao_api_key)
                    
                    # 중복 확인
                    existing_id = get_existing_map_id(cur, row["name"], row["address_detail"], lat, lng)
                    if existing_id:
                        map_id = existing_id
                        # 기존 정보 업데이트 (좌표 등 보정)
                        cur.execute(
                            "UPDATE maps SET latitude = %s, longitude = %s WHERE map_id = %s",
                            (lat, lng, map_id)
                        )
                    else:
                        cur.execute(
                            """
                            INSERT INTO maps (name, category_cd, address_cd, address_detail, latitude, longitude)
                            VALUES (%s, %s, %s, %s, %s, %s)
                            RETURNING map_id
                            """,
                            (row["name"], row["category_cd"], row["address_cd"], row["address_detail"], lat, lng),
                        )
                        map_id = cur.fetchone()[0]
                    
                    map_id_lookup[(row["name"], row["address_detail"])] = map_id

                shop_id_lookup: Dict[Tuple[str, str], int] = {}
                for row in shop_df.to_dict("records"):
                    key = (row["store_name"], row["store_address"])
                    map_id = map_id_lookup.get(key)
                    if map_id is None:
                        continue
                    
                    # shop 테이블 중복 확인 (이미 해당 map_id로 등록된 상세 정보가 있는지)
                    cur.execute("SELECT shop_id FROM shop WHERE map_id = %s AND category_cd = %s", (map_id, row["category_cd"]))
                    shop_row = cur.fetchone()
                    if shop_row:
                        shop_id = shop_row[0]
                        cur.execute("UPDATE shop SET rating = %s WHERE shop_id = %s", (row["rating"], shop_id))
                    else:
                        cur.execute(
                            "INSERT INTO shop (map_id, category_cd, rating) VALUES (%s, %s, %s) RETURNING shop_id",
                            (map_id, row["category_cd"], row["rating"]),
                        )
                        shop_id = cur.fetchone()[0]
                    shop_id_lookup[key] = shop_id

                for row in menu_df.to_dict("records"):
                    key = (row["store_name"], row["store_address"])
                    shop_id = shop_id_lookup.get(key)
                    if shop_id is None:
                        continue
                    
                    price_val = None if pd.isna(row["price"]) else int(row["price"])
                    # menu 테이블 중복 확인 (가게 ID와 메뉴명 기반)
                    cur.execute("SELECT menu_id FROM menu WHERE shop_id = %s AND name = %s", (shop_id, row["name"]))
                    menu_row = cur.fetchone()
                    if menu_row:
                        cur.execute("UPDATE menu SET price = %s WHERE menu_id = %s", (price_val, menu_row[0]))
                    else:
                        cur.execute("INSERT INTO menu (shop_id, name, price) VALUES (%s, %s, %s)", (shop_id, row["name"], price_val))

    finally:
        conn.close()

def main() -> None:
    parser = argparse.ArgumentParser(description="맛집 raw 데이터를 전처리 후 PostgreSQL 업로드")
    
    # common_utils의 PARENT_DIR 활용 (이미 위에서 정의됨)
    BASE_DIR = CURRENT_DIR.parent
    PROJECT_ROOT = PARENT_DIR.parent
    
    parser.add_argument("--input", default=str(BASE_DIR / "data" / "raw_store_data.csv"))
    parser.add_argument("--output-dir", default=str(BASE_DIR / "data"))
    parser.add_argument("--archive-dir", default=str(BASE_DIR / "data" / "archives"))
    parser.add_argument("--code-table", default=str(PROJECT_ROOT / "database" / "data" / "codeT.csv"))
    parser.add_argument("--default-category-cd", default=FoodCategory.KOREAN.value)
    parser.add_argument("--default-address-cd", default=Location.DEFAULT.value)
    parser.add_argument("--host", required=True)
    parser.add_argument("--port", type=int, default=5432)
    parser.add_argument("--dbname", required=True)
    parser.add_argument("--user", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--truncate-first", action="store_true")
    parser.add_argument("--kakao-api-key", default="", help="카카오 REST API 키 (위경도 파싱용)")
    args = parser.parse_args()

    # 데이터 로드 및 변환
    maps_df, shop_df, menu_df = load_and_transform(args.input, args.code_table, args.default_category_cd, args.default_address_cd)
    
    # 중간 산출물 저장
    save_intermediate(maps_df, shop_df, menu_df, args.output_dir)
    
    try:
        # DB 업로드 (트랜잭션 및 중복 체크 포함)
        upload(
            maps_df,
            shop_df,
            menu_df,
            {
                "host": args.host,
                "port": args.port,
                "dbname": args.dbname,
                "user": args.user,
                "password": args.password,
            },
            truncate_first=args.truncate_first,
            kakao_api_key=args.kakao_api_key,
        )
        print("✅ DB 업로드 완료. 파일 아카이빙을 시작합니다.")
        
        # 업로드 성공 후 아카이빙 처리
        out_dir = Path(args.output_dir)
        archive_files([
            str(out_dir / "maps.csv"),
            str(out_dir / "shop.csv"),
            str(out_dir / "menu.csv"),
            str(out_dir / "shop_candidates.csv"),
            args.input # 원본 데이터도 아카이브 대상으로 포함
        ], args.archive_dir)
        
    except Exception as e:
        print(f"❌ DB 작업 중 치명적 오류 발생 (롤백됨): {e}")
        raise

if __name__ == "__main__":
    main()
