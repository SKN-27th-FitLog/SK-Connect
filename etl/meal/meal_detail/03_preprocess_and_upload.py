import os
import requests
import argparse
import json
from pathlib import Path
from typing import Dict, List, Tuple

import pandas as pd
import psycopg2
from psycopg2.extras import execute_values

MAPS_COLUMNS = ["name", "category_cd", "address_cd", "address_detail", "latitude", "longitude"]
SHOP_COLUMNS = ["map_id", "category_cd", "rating"]
MENU_COLUMNS = ["shop_id", "name", "price"]


def load_code_tables(code_csv: str) -> Tuple[Dict[str, str], Dict[str, str]]:
    df_cd = pd.read_csv(code_csv)
    category_map = {str(row["name"]).strip(): str(row["cd"]).strip() for _, row in df_cd.iterrows() if str(row["cd"]).strip().startswith(("FC", "CA"))}
    address_map = {str(row["name"]).strip(): str(row["cd"]).strip() for _, row in df_cd.iterrows() if str(row["cd_upper"]).strip() == "LA00"}
    return category_map, address_map

def load_and_transform(raw_csv: str, code_csv: str, default_category_cd: str, default_address_cd: str) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    category_map, address_map = load_code_tables(code_csv)
    df = pd.read_csv(raw_csv)
    df = df[df["status"] == "ok"].copy()
    df["store_name"] = df["store_name"].fillna("").astype(str).str.strip()
    df["store_address"] = df["store_address"].fillna("").astype(str).str.strip()
    df = df[(df["store_name"] != "") & (df["store_address"] != "")].copy()

    # 여기 좌표는 현재 단계에서 별도 보강해야 함. 일단 컬럼만 유지.
    df["latitude"] = 0.0
    df["longitude"] = 0.0
    
    def get_cat_cd(c) -> str:
        if pd.isna(c) or c == "":
            return default_category_cd
        return category_map.get(str(c).strip(), default_category_cd)

    def get_addr_info(a) -> pd.Series:
        a_str = str(a).strip()
        for key in sorted(address_map.keys(), key=len, reverse=True):
            if a_str.startswith(key):
                return pd.Series([address_map[key], a_str[len(key):].strip()])
        return pd.Series([default_address_cd, a_str])

    # maps category_cd is fixed to 'CA01' (맛집) per init.sql map constraint
    # shop category_cd is the detailed food category (e.g. FC01)
    df["shop_category_cd"] = df["source_category"].apply(get_cat_cd) if "source_category" in df.columns else default_category_cd
    df["category_cd"] = "CA01"
        
    df[["address_cd", "store_address"]] = df["store_address"].apply(get_addr_info)

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


def fetch_coordinates_kakao(address: str, api_key: str) -> Tuple[float, float]:
    if not api_key:
        return 0.0, 0.0
    url = "https://dapi.kakao.com/v2/local/search/address.json"
    headers = {"Authorization": f"KakaoAK {api_key}"}
    try:
        resp = requests.get(url, headers=headers, params={"query": address}, timeout=5)
        if resp.status_code == 200:
            docs = resp.json().get("documents", [])
            if docs:
                return float(docs[0].get("y", 0.0)), float(docs[0].get("x", 0.0))
    except Exception as e:
        print(f"Kakao API Error for {address}: {e}")
    return 0.0, 0.0

def upload(maps_df: pd.DataFrame, shop_df: pd.DataFrame, menu_df: pd.DataFrame, conn_args: Dict[str, str], truncate_first: bool, kakao_api_key: str = "") -> None:
    conn = psycopg2.connect(**conn_args)
    try:
        with conn:
            with conn.cursor() as cur:
                if truncate_first:
                    cur.execute("TRUNCATE TABLE menu, shop, maps RESTART IDENTITY CASCADE")

                map_id_lookup: Dict[Tuple[str, str], int] = {}
                for row in maps_df.to_dict("records"):
                    lat, lng = row["latitude"], row["longitude"]
                    if lat == 0.0 and lng == 0.0 and kakao_api_key:
                        lat, lng = fetch_coordinates_kakao(row["address_detail"], kakao_api_key)
                        
                    cur.execute(
                        """
                        INSERT INTO maps (name, category_cd, address_cd, address_detail, latitude, longitude)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        RETURNING map_id
                        """,
                        (
                            row["name"],
                            row["category_cd"],
                            row["address_cd"],
                            row["address_detail"],
                            lat,
                            lng,
                        ),
                    )
                    map_id = cur.fetchone()[0]
                    map_id_lookup[(row["name"], row["address_detail"])] = map_id

                shop_id_lookup: Dict[Tuple[str, str], int] = {}
                for row in shop_df.to_dict("records"):
                    key = (row["store_name"], row["store_address"])
                    map_id = map_id_lookup.get(key)
                    if map_id is None:
                        continue
                    cur.execute(
                        "INSERT INTO shop (map_id, category_cd, rating) VALUES (%s, %s, %s) RETURNING shop_id",
                        (map_id, row["category_cd"], row["rating"]),
                    )
                    shop_id = cur.fetchone()[0]
                    shop_id_lookup[key] = shop_id

                menu_values = []
                for row in menu_df.to_dict("records"):
                    key = (row["store_name"], row["store_address"])
                    shop_id = shop_id_lookup.get(key)
                    if shop_id is None:
                        continue
                    menu_values.append((shop_id, row["name"], None if pd.isna(row["price"]) else int(row["price"])))

                if menu_values:
                    execute_values(cur, "INSERT INTO menu (shop_id, name, price) VALUES %s", menu_values)
    finally:
        conn.close()


def cleanup_files(files: List[str]) -> None:
    for f in files:
        if os.path.exists(f):
            try:
                os.remove(f)
                print(f"✅ 삭제 완료: {f}")
            except Exception as e:
                print(f"❌ 삭제 실패 {f}: {e}")

def main() -> None:
    parser = argparse.ArgumentParser(description="맛집 raw 데이터를 전처리 후 PostgreSQL 업로드")
    BASE_DIR = Path(__file__).resolve().parent.parent
    PROJECT_ROOT = BASE_DIR.parent.parent
    
    parser.add_argument("--input", default=str(BASE_DIR / "data" / "raw_store_data.csv"))
    parser.add_argument("--output-dir", default=str(BASE_DIR / "data"))
    parser.add_argument("--code-table", default=str(PROJECT_ROOT / "database" / "data" / "codeT.csv"))
    parser.add_argument("--default-category-cd", default="FC01")
    parser.add_argument("--default-address-cd", default="LA00")
    parser.add_argument("--host", required=True)
    parser.add_argument("--port", type=int, default=5432)
    parser.add_argument("--dbname", required=True)
    parser.add_argument("--user", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--truncate-first", action="store_true")
    parser.add_argument("--kakao-api-key", default="", help="카카오 REST API 키 (위경도 파싱용)")
    args = parser.parse_args()

    maps_df, shop_df, menu_df = load_and_transform(args.input, args.code_table, args.default_category_cd, args.default_address_cd)
    save_intermediate(maps_df, shop_df, menu_df, args.output_dir)
    try:
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
        print("✅ DB 업로드 완료. 임시 파일 삭제를 시작합니다.")
        # Upload successful, cleanup CSVs
        out_dir = Path(args.output_dir)
        cleanup_files([
            args.input,
            str(out_dir / "maps.csv"),
            str(out_dir / "shop.csv"),
            str(out_dir / "menu.csv"),
            str(out_dir / "shop_candidates.csv")
        ])
    except Exception as e:
        print(f"❌ DB 업로드 실패: {e}")
        raise


if __name__ == "__main__":
    main()
