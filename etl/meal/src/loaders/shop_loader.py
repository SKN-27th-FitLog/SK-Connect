import json
import pandas as pd
from typing import Dict, Any, List, Tuple
from ..core.db_client import DBClient
from ..core.services.kakao_api import KakaoAPI
from ..core.file_manager import logger, file_manager
from ..transformers.shop_processor import ShopProcessor
from ..core.constants import Category, LoadStatus

class ShopLoader:
    """
    식당 데이터를 [Raw -> Cleansing -> DB Load -> Save] 단계별로 관리하며,
    엄격한 무결성 검증을 통해 부실 데이터의 DB 유입을 차단합니다 (Gatekeeper).
    v3.1: Kakao API 실패 시 상세 페이지 추출 좌표를 Fallback으로 사용합니다.
    """
    
    def __init__(self, db_client: DBClient, kakao_api: KakaoAPI, processor: ShopProcessor):
        self.db = db_client
        self.kakao = kakao_api
        self.processor = processor
        self.map_category_cd = Category.RESTAURANT.value

    def load_all(self, df_raw: pd.DataFrame) -> Dict[str, int]:
        """
        [무결성 게이트키퍼] 전체 적재 흐름 및 무결성 제어.
        """
        if df_raw.empty:
            logger.warning("--- [LOADER] 처리할 데이터가 없습니다.")
            return {"success": 0, "fail": 0}

        # 1. RAW 저장
        file_manager.save_df(df_raw, "raw", "shop", LoadStatus.SUCCESS.value)

        # 2. 전처리 및 무결성 검증 (Fallback Geocoding 포함)
        valid_items, fail_items = self._process_and_validate(df_raw)

        # 3. [CLEANSING] 단계 저장 (이원화)
        if valid_items:
            df_success = pd.DataFrame(valid_items)
            file_manager.save_df(df_success, "cleansing", "shop", LoadStatus.SUCCESS.value)
        
        if fail_items:
            df_fail = pd.DataFrame(fail_items)
            file_manager.save_df(df_fail, "cleansing", "shop", LoadStatus.FAIL.value)

        # 4. DB 적재 (성공 건만 진행)
        success_db_count = 0
        if valid_items:
            success_db_count = self._load_to_db(valid_items)

        # 5. [SAVE] 단계 저장
        if success_db_count > 0:
            df_final = pd.DataFrame(valid_items[:success_db_count])
            file_manager.save_df(df_final, "save", "shop", LoadStatus.SUCCESS.value)
            
        return {"success": success_db_count, "fail": len(fail_items)}

    def _process_and_validate(self, df: pd.DataFrame) -> Tuple[List[Dict], List[Dict]]:
        valid_list = []
        fail_list = []

        for _, row in df.iterrows():
            # 1. 좌표 수집 (우선순위: Kakao API -> Page Fallback)
            lat, lon = self.kakao.get_coordinates(str(row.get("store_address", "")))
            
            if lat is None or lon is None or (lat == 0.0 and lon == 0.0):
                # Kakao API 실패 시 수집기에서 가져온 좌표 시도
                p_lat = float(row.get("latitude", 0.0))
                p_lon = float(row.get("longitude", 0.0))
                if p_lat != 0.0 and p_lon != 0.0:
                    lat, lon = p_lat, p_lon
                    logger.info(f"--- [Fallback] Kakao API 실패로 페이지 추출 좌표 사용: {p_lat}, {p_lon}")

            # 2. 전처리
            p_data = self.processor.process_for_master(row, lat, lon)
            
            # 3. 무결성 검증
            errors = self.processor.validate_master_data(p_data)
            
            if errors:
                p_data["fail_reason"] = ", ".join(errors)
                fail_list.append(p_data)
            else:
                # 4. 이미지 처리
                try:
                    urls = json.loads(str(row.get("shop_image_urls", "[]")))
                    local_paths = []
                    for url in urls:
                        path = file_manager.download_image(url, p_data["name"], prefix="shop")
                        if path: local_paths.append(path)
                    p_data["local_image_paths"] = json.dumps(local_paths, ensure_ascii=False)
                except:
                    p_data["local_image_paths"] = "[]"
                    
                valid_list.append(p_data)
                
        return valid_list, fail_list

    def _load_to_db(self, valid_items: List[Dict[str, Any]]) -> int:
        def task(conn, cur):
            success = 0
            for p_data in valid_items:
                try:
                    cur.execute(
                        "INSERT INTO maps (name, category_cd, address_cd, address_detail, latitude, longitude) "
                        "VALUES (%s, %s, %s, %s, %s, %s) RETURNING map_id",
                        (p_data["name"], self.map_category_cd, p_data["address_cd"], 
                         p_data["address_detail"], p_data["latitude"], p_data["longitude"])
                    )
                    map_id = cur.fetchone()[0]

                    cur.execute(
                        "INSERT INTO shop (map_id, category_cd, rating) VALUES (%s, %s, %s) RETURNING shop_id",
                        (map_id, p_data["food_category_cd"], p_data["rating"])
                    )
                    shop_id = cur.fetchone()[0]

                    self._load_menus(cur, shop_id, p_data["menus_json"])
                    self._load_shop_images(cur, shop_id, p_data.get("local_image_paths", "[]"))
                    success += 1
                except Exception as e:
                    logger.error(f"!!! DB 적재 실패: {e}")
            return success
        return self.db.execute_transaction(task)

    def _load_menus(self, cur, shop_id: int, menus_json: str):
        try:
            m_list = json.loads(menus_json)
            for m in m_list:
                name = str(m.get("menu_name", "")).strip()[:100]
                price = self.processor.safe_int(m.get("menu_price"))
                if name:
                    cur.execute("INSERT INTO menu (shop_id, name, price) VALUES (%s, %s, %s)",
                                (shop_id, name, price))
        except: pass

    def _load_shop_images(self, cur, shop_id: int, paths_json: str):
        try:
            paths = json.loads(paths_json)
            for p in paths:
                cur.execute("INSERT INTO images (image_url, table_name, table_id) VALUES (%s, %s, %s)",
                            (p, "shop", shop_id))
        except: pass
