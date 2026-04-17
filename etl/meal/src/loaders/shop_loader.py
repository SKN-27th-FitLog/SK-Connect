import json
import pandas as pd
from typing import Dict, Any, List
from ..core.db_client import DBClient
from ..core.services.kakao_api import KakaoAPI
from ..core.file_manager import logger, file_manager
from ..transformers.shop_processor import ShopProcessor
from ..core.constants import Category

class ShopLoader:
    """
    식당 데이터를 [Raw -> Cleansing -> DB Load -> Save] 단계별로 관리합니다.
    (기존 PLAN.MD 및 MODIFY_RULE.MD의 저장 규약을 엄격히 준수)
    """
    
    def __init__(self, db_client: DBClient, kakao_api: KakaoAPI, processor: ShopProcessor):
        self.db = db_client
        self.kakao = kakao_api
        self.processor = processor
        self.map_category_cd = Category.RESTAURANT.value

    def load_all(self, df_raw: pd.DataFrame) -> Dict[str, int]:
        """
        수집된 원본 데이터를 받아서 전체 ETL 저장/적재 흐름을 수행합니다.
        """
        if df_raw.empty:
            logger.warning("--- [LOADER] 처리할 데이터가 없습니다.")
            return {"success": 0, "skip": 0}

        # 1. RAW 저장 (수집 직후 파일 보존)
        file_manager.save_df(df_raw, "raw", "shop", "success")

        # 2. CLEANSING 수행 및 저장 (정제 완료 파일 보존)
        cleansed_shops, cleansed_menus = self._preprocess_all(df_raw)
        
        df_shop_c = pd.DataFrame(cleansed_shops)
        file_manager.save_df(df_shop_c, "cleansing", "shop", "success")
        
        if cleansed_menus:
            df_menu_c = pd.DataFrame(cleansed_menus)
            file_manager.save_df(df_menu_c, "cleansing", "menu", "success")

        # 3. DB 적재 (Master 테이블)
        success_count, skip_count = self._load_to_master_tables(cleansed_shops)

        # 4. SAVE 저장 (적재 성공 내역 보존)
        if success_count > 0:
            file_manager.save_df(df_shop_c, "save", "shop", "success")
            
        return {"success": success_count, "skip": skip_count}

    def _preprocess_all(self, df: pd.DataFrame):
        """데이터를 상위/하위 테이블 구조로 분리 및 정제"""
        shops = []
        menus = []
        for _, row in df.iterrows():
            p_data = self.processor.process_for_master(row)
            shops.append(p_data)
            
            # 메뉴 분리
            try:
                m_list = json.loads(p_data["menus_json"])
                for m in m_list:
                    m["store_name"] = p_data["name"]
                    menus.append(m)
            except: pass
        return shops, menus

    def _load_to_master_tables(self, shops: List[Dict[str, Any]]):
        """DB 트랜잭션을 통한 마스터 테이블 적재"""
        def task(conn, cur):
            success = 0
            skip = 0
            for p_data in shops:
                try:
                    # 1. 위경도 및 maps 적재
                    lat, lon = self.kakao.get_coordinates(p_data["address_detail"])
                    cur.execute(
                        "SELECT map_id FROM maps WHERE name = %s AND address_detail = %s",
                        (p_data["name"], p_data["address_detail"])
                    )
                    row = cur.fetchone()
                    if row: map_id = row[0]
                    else:
                        cur.execute(
                            "INSERT INTO maps (name, category_cd, address_cd, address_detail, latitude, longitude) "
                            "VALUES (%s, %s, %s, %s, %s, %s) RETURNING map_id",
                            (p_data["name"], self.map_category_cd, p_data["address_cd"], 
                             p_data["address_detail"], lat, lon)
                        )
                        map_id = cur.fetchone()[0]

                    # 2. shop 적재
                    cur.execute("SELECT shop_id FROM shop WHERE map_id = %s", (map_id,))
                    row = cur.fetchone()
                    if row: shop_id = row[0]
                    else:
                        cur.execute(
                            "INSERT INTO shop (map_id, category_cd, rating) VALUES (%s, %s, %s) RETURNING shop_id",
                            (map_id, p_data["food_category_cd"], p_data["rating"])
                        )
                        shop_id = cur.fetchone()[0]

                    # 3. menu 적재
                    self._load_menus(cur, shop_id, p_data["menus_json"])
                    success += 1
                except Exception as e:
                    logger.error(f"!!! [{p_data['name']}] 적재 실패: {e}")
                    skip += 1
            return success, skip

        return self.db.execute_transaction(task)

    def _load_menus(self, cur, shop_id: int, menus_json: str):
        try:
            m_list = json.loads(menus_json)
            for m in m_list:
                name = str(m.get("menu_name", "")).strip()[:100]
                price = self.processor.safe_int(m.get("menu_price"))
                if name:
                    cur.execute("SELECT 1 FROM menu WHERE shop_id = %s AND name = %s", (shop_id, name))
                    if not cur.fetchone():
                        cur.execute("INSERT INTO menu (shop_id, name, price) VALUES (%s, %s, %s)",
                                    (shop_id, name, price))
        except: pass
