import sys
import argparse
import json
import math
import os
from pathlib import Path
from typing import Dict, List, Optional, Final, Tuple

import pandas as pd
import psycopg2
from psycopg2.extensions import connection, cursor

# 상위 디렉토리의 유틸리티 및 상수 임포트
CURRENT_DIR: Final[Path] = Path(__file__).resolve().parent
PROJECT_ROOT: Final[Path] = CURRENT_DIR.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from common_utils import logger, fetch_coordinates_kakao, get_project_root
from members import Category, FoodCategory, Location

# maps 테이블의 category_cd: 맛집 전체는 CA01(RESTAURANT) 고정
# shop 테이블의 category_cd: 음식 세부 분류(FC01~FC06) 사용
DEFAULT_MAP_CATEGORY: Final[str] = Category.RESTAURANT.value  # "CA01"
DEFAULT_FOOD_CATEGORY: Final[str] = FoodCategory.FUSION.value   # "FC06" (기타/미분류)
DEFAULT_ADDRESS_CD: Final[str] = Location.DEFAULT.value          # "LA00" (기본 지역)


# -----------------------------------------------------------------------
# [신규] NaN / None / 범위 초과값 안전 변환 헬퍼
# menu.price 는 DB 에서 INT 이므로 범위 초과 입력 시 오류가 발생한다.
# upload_to_db.py 와 동일한 패턴을 적용하여 일관성 유지.
# -----------------------------------------------------------------------
_INT_MAX: Final[int] = 2_147_483_647
_INT_MIN: Final[int] = -2_147_483_648


def _safe_int(value: object, default: int = 0) -> int:
    """NaN / None / 범위 초과값을 INT 로 안전하게 변환합니다."""
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


def load_code_tables(code_csv: str) -> Tuple[Dict[str, str], Dict[str, str]]:
    """
    codeT.csv 에서 카테고리 코드와 지역 코드 매핑을 로드합니다.
    - category_map : { 음식분류명 → FC코드 }
    - address_map  : { 지역명     → LA코드 }
    """
    try:
        df_cd: pd.DataFrame = pd.read_csv(code_csv)
        # FC/CA 로 시작하는 코드를 카테고리 맵으로 구성 (음식 분류 우선)
        category_map: Dict[str, str] = {
            str(row["name"]).strip(): str(row["cd"]).strip()
            for _, row in df_cd.iterrows()
            if str(row["cd"]).strip().startswith(("FC", "CA"))
        }
        # LA00 하위에 있는 지역 코드를 주소 맵으로 구성
        address_map: Dict[str, str] = {
            str(row["name"]).strip(): str(row["cd"]).strip()
            for _, row in df_cd.iterrows()
            if str(row.get("cd_upper", "")).strip() == Location.DEFAULT.value
        }
        return category_map, address_map
    except Exception as e:
        logger.error(f"⚠️ 코드 테이블 로드 실패: {e}")
        return {}, {}


def resolve_address_cd(address: str, address_map: Dict[str, str]) -> str:
    """
    주소 문자열을 스캔하여 매칭되는 지역 코드를 반환합니다.
    일치하는 지역명이 없으면 기본값(LA00)을 사용합니다.
    maps 테이블의 address_cd 컬럼은 NOT NULL 이므로 반드시 기본값 반환 필요.
    """
    for name, cd in address_map.items():
        if name in address:
            return cd
    return DEFAULT_ADDRESS_CD


def resolve_food_category(source_category: str, category_map: Dict[str, str]) -> str:
    """
    수집된 카테고리 문자열에서 FC(음식 세부 분류) 코드를 찾아 반환합니다.
    매핑 실패 시 FUSION(FC06, 기타)을 기본값으로 사용합니다.
    """
    for name, cd in category_map.items():
        if name in source_category and cd.startswith("FC"):
            return cd
    return DEFAULT_FOOD_CATEGORY


def insert_maps_shop_menu(
    df: pd.DataFrame,
    conn_args: Dict[str, str],
    kakao_api_key: str,
    category_map: Dict[str, str],
    address_map: Dict[str, str],
) -> None:
    """
    collect_details 수집 결과를 maps / shop / menu 테이블에 적재합니다.

    처리 흐름:
      1. store_address → Kakao API → (latitude, longitude)
      2. maps 테이블 INSERT (name + address_detail 기준 중복 방지)
      3. shop 테이블 INSERT (map_id FK 연결, map_id 기준 중복 방지)
      4. menus_json 파싱 → menu 테이블 INSERT (shop_id + name 기준 중복 방지)
    """
    if df.empty:
        logger.warning("💡 적재할 데이터가 없습니다.")
        return

    conn: connection = psycopg2.connect(**conn_args)
    try:
        # 단일 트랜잭션으로 묶어서 부분 실패 시 전체 롤백되도록 함
        with conn:
            with conn.cursor() as cur:
                cur: cursor = cur  # 타입 힌트 보정
                success_count: int = 0
                skip_count: int = 0

                for _, row in df.iterrows():
                    store_name: str = str(row.get("store_name", "")).strip()
                    if not store_name:
                        # store_name 이 없으면 maps/shop 에 INSERT 할 수 없으므로 스킵
                        skip_count += 1
                        continue

                    store_address: str = str(row.get("store_address", ""))
                    store_rating: float = _safe_float(row.get("store_rating"))
                    source_category: str = str(row.get("source_category", ""))
                    menus_json_str: str = str(row.get("menus_json", "[]"))

                    # ----------------------------------------------------------
                    # [신규] Kakao API 위경도 조회
                    # common_utils.fetch_coordinates_kakao 는 정의되어 있었으나
                    # 어떤 스크립트에서도 실제로 호출하지 않아 위경도가 전부 0.0
                    # 이었음. 이 스크립트에서 최초로 실제 호출하여 maps 테이블의
                    # latitude/longitude 컬럼에 정확한 값을 채운다.
                    # ----------------------------------------------------------
                    latitude: float
                    longitude: float
                    if kakao_api_key:
                        latitude, longitude = fetch_coordinates_kakao(store_address, kakao_api_key)
                        if latitude == 0.0 and longitude == 0.0:
                            logger.warning(f"⚠️ 위경도 조회 실패 (기본값 0.0 사용): {store_name}")
                    else:
                        # API 키 미설정 시 0.0 fallback (개발/테스트 환경 대비)
                        latitude, longitude = 0.0, 0.0
                        logger.warning(f"⚠️ KAKAO_API_KEY 미설정 — 위경도 0.0 으로 저장: {store_name}")

                    # 지역 코드 & 음식 카테고리 코드 결정
                    address_cd: str = resolve_address_cd(store_address, address_map)
                    food_cat_cd: str = resolve_food_category(source_category, category_map)

                    # ----------------------------------------------------------
                    # maps 테이블 INSERT
                    # 동일한 (name, address_detail) 조합이 이미 있으면 INSERT 생략.
                    # 중복 적재를 막아 maps.map_id 가 여러 개 생기는 것을 방지.
                    # ----------------------------------------------------------
                    cur.execute(
                        "SELECT map_id FROM maps WHERE name = %s AND address_detail = %s",
                        (store_name, store_address),
                    )
                    existing_map = cur.fetchone()
                    if existing_map:
                        map_id: int = existing_map[0]
                        logger.debug(f"⏭️ maps 중복 스킵 (map_id={map_id}): {store_name}")
                    else:
                        cur.execute(
                            """
                            INSERT INTO maps (name, category_cd, address_cd, address_detail, latitude, longitude)
                            VALUES (%s, %s, %s, %s, %s, %s)
                            RETURNING map_id
                            """,
                            (store_name, DEFAULT_MAP_CATEGORY, address_cd, store_address, latitude, longitude),
                        )
                        map_res = cur.fetchone()
                        if not map_res:
                            logger.error(f"❌ maps INSERT 실패: {store_name}")
                            continue
                        map_id = map_res[0]

                    # ----------------------------------------------------------
                    # shop 테이블 INSERT
                    # 같은 map_id 에 대한 shop 이 이미 있으면 INSERT 생략.
                    # map_id 는 1:1 관계이므로 map_id 로만 중복 체크.
                    # ----------------------------------------------------------
                    cur.execute("SELECT shop_id FROM shop WHERE map_id = %s", (map_id,))
                    existing_shop = cur.fetchone()
                    if existing_shop:
                        shop_id: int = existing_shop[0]
                        logger.debug(f"⏭️ shop 중복 스킵 (shop_id={shop_id}): {store_name}")
                    else:
                        cur.execute(
                            """
                            INSERT INTO shop (map_id, category_cd, rating)
                            VALUES (%s, %s, %s)
                            RETURNING shop_id
                            """,
                            (map_id, food_cat_cd, store_rating),
                        )
                        shop_res = cur.fetchone()
                        if not shop_res:
                            logger.error(f"❌ shop INSERT 실패: {store_name}")
                            continue
                        shop_id = shop_res[0]

                    # ----------------------------------------------------------
                    # menu 테이블 INSERT
                    # collect_details 가 menus_json 컬럼에 JSON 배열로 저장.
                    # 파싱 실패(빈 배열 포함)해도 maps/shop 은 이미 적재 완료이므로
                    # 예외를 무시하고 계속 진행.
                    # ----------------------------------------------------------
                    try:
                        menus: List[Dict[str, str]] = json.loads(menus_json_str)
                    except (json.JSONDecodeError, TypeError):
                        menus = []

                    for menu_item in menus:
                        menu_name: str = str(menu_item.get("menu_name", "")).strip()[:100]
                        menu_price: int = _safe_int(menu_item.get("menu_price"))
                        if not menu_name:
                            continue
                        # 같은 가게의 동일 메뉴명 중복 방지
                        cur.execute(
                            "SELECT menu_id FROM menu WHERE shop_id = %s AND name = %s",
                            (shop_id, menu_name),
                        )
                        if not cur.fetchone():
                            cur.execute(
                                "INSERT INTO menu (shop_id, name, price) VALUES (%s, %s, %s)",
                                (shop_id, menu_name, menu_price),
                            )

                    success_count += 1

                logger.info(
                    f"✅ maps/shop/menu 적재 완료 — 성공: {success_count}건, 스킵: {skip_count}건"
                )
    except Exception as e:
        logger.error(f"❌ maps/shop/menu 적재 중 치명적 오류 발생: {str(e)}")
        raise
    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="[Next-Gen] 맛집 상세 정보 DB 적재 — maps / shop / menu 테이블"
    )
    parser.add_argument("--input", required=True, help="collect_details 단계 raw CSV")
    parser.add_argument("--code-table", required=True, help="codeT.csv 경로")
    parser.add_argument(
        "--kakao-api-key",
        default=os.environ.get("KAKAO_API_KEY", ""),
        help="카카오 REST API 키 (미설정 시 위경도 0.0 저장)",
    )
    parser.add_argument("--host", required=True)
    parser.add_argument("--port", type=int, default=5432)
    parser.add_argument("--dbname", required=True)
    parser.add_argument("--user", required=True)
    parser.add_argument("--password", required=True)

    args = parser.parse_args()

    # 1. 수집 데이터 로드 (status=ok 인 행만 적재 대상)
    logger.info(f"📥 원본 데이터 로드: {args.input}")
    try:
        df: pd.DataFrame = pd.read_csv(args.input)
        # collect_details 가 성공적으로 수집한 행만 사용
        df = df[df["status"] == "ok"].copy()
        logger.info(f"📊 적재 대상 가게: {len(df)}건")
    except Exception as e:
        logger.error(f"데이터 로드 실패: {str(e)}")
        return

    # 2. 코드 테이블 로드 (카테고리/지역 코드 매핑)
    category_map, address_map = load_code_tables(args.code_table)

    # 3. DB 연결 정보 구성
    conn_args: Dict[str, str] = {
        "host": args.host,
        "port": str(args.port),
        "dbname": args.dbname,
        "user": args.user,
        "password": args.password,
    }

    # 4. maps / shop / menu 테이블 적재 실행
    insert_maps_shop_menu(df, conn_args, args.kakao_api_key, category_map, address_map)


if __name__ == "__main__":
    main()
