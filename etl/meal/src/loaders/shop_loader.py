import json
import pandas as pd
from typing import Dict, Any, List, Tuple
from ..core.db_client import DBClient
from ..core.services.kakao_api import KakaoAPI
from ..core.file_manager import logger
from ..transformers.shop_processor import ShopProcessor
from .base_loader import BaseLoader
from ..core.constants.schema_constants import MapsColumns, ShopColumns, MenuColumns
from ..core.constants.pipeline_constants import LoadStatus, ProcessType, CrawlerThread

class ShopLoader(BaseLoader):
    """
    식당 데이터를 [RAW -> CLEANING -> DB -> SAVE] 단계별로 관리하며,
    스키마 계약에 따른 엄격한 무결성 검증과 중복 체크를 수행합니다.
    """
    
    def __init__(self, db_client: DBClient, kakao_api: KakaoAPI, processor: ShopProcessor):
        super().__init__(db_client)
        self.kakao = kakao_api
        self.processor = processor

    def load_all(self, df_raw: pd.DataFrame) -> Dict[str, int]:
        if df_raw.empty:
            logger.warning("--- [LOADER] 처리할 데이터가 없습니다.")
            return {"success": 0, "fail": 0}

        # 1. CRAWLING(RAW) 저장
        self.save_with_status(df_raw, ProcessType.CRAWLING, CrawlerThread.SHOP.value, LoadStatus.SUCCESS)

        # 2. 전처리 및 스키마 검증
        valid_items, fail_items = self._process_and_validate(df_raw)

        # 3. [CLEANING] 단계 저장 (이원화)
        if valid_items:
            self.save_with_status(pd.DataFrame(valid_items), ProcessType.CLEANING, CrawlerThread.SHOP.value, LoadStatus.SUCCESS)
        
        if fail_items:
            self.save_with_status(pd.DataFrame(fail_items), ProcessType.CLEANING, CrawlerThread.SHOP.value, LoadStatus.FAIL)

        # 4. DB 적재 (중복 체크 포함)
        success_db_items = []
        for item in valid_items:
            # 중복 체크 (1순위 URL, 2순위 Name+Address)
            exists, existing_id = self.sync_service.exists_in_db("maps", item)
            if exists:
                logger.info(f"--- [SKIP] 이미 존재하는 매장: {item.get(MapsColumns.NAME.value)}")
                continue
                
            # 실제 적재
            db_success = self._load_single_item(item)
            if db_success:
                success_db_items.append(item)

        # 5. [SAVE] 단계 저장
        if success_db_items:
            self.save_with_status(pd.DataFrame(success_db_items), ProcessType.SAVE, CrawlerThread.SHOP.value, LoadStatus.SUCCESS)
            
        return {"success": len(success_db_items), "fail": len(fail_items)}

    def _process_and_validate(self, df: pd.DataFrame) -> Tuple[List[Dict], List[Dict]]:
        valid_list = []
        fail_list = []

        for _, row in df.iterrows():
            # 1. 좌표 수집
            lat, lon = self.kakao.get_coordinates(str(row.get("store_address", "")))
            if lat is None or (lat == 0.0 and lon == 0.0):
                lat, lon = float(row.get("latitude", 0.0)), float(row.get("longitude", 0.0))

            # 2. 전처리
            p_data = self.processor.process_for_master(row, lat, lon)
            
            # 3. 스키마 계약 검증 (v4.0 Strict Policy)
            is_valid, error = self.validator.validate("maps", p_data)
            
            if not is_valid:
                # 실패 메타데이터 보강
                p_data = self.record_failure(p_data, stage="validation", reason=error)
                fail_list.append(p_data)
                continue

            # 4. 이미지 다운로드 및 로컬 경로 확보
            p_data[ShopColumns.KEYWORDS.value] = row.get("keywords", "[]")
            valid_list.append(p_data)
                
        return valid_list, fail_list

    def _load_single_item(self, item: Dict[str, Any]) -> bool:
        """단일 매장 및 관련 정보 DB 적재 트랜잭션"""
        def task(conn, cur):
            try:
                # maps INSERT
                cur.execute(
                    f"INSERT INTO maps ({MapsColumns.NAME.value}, category_cd, address_cd, {MapsColumns.ADDRESS_DETAIL.value}, "
                    f"{MapsColumns.LATITUDE.value}, {MapsColumns.LONGITUDE.value}, {MapsColumns.SOURCE_URL.value}) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING map_id",
                    (item[MapsColumns.NAME.value], item["maps_category_cd"], item["address_cd"], 
                     item[MapsColumns.ADDRESS_DETAIL.value], item[MapsColumns.LATITUDE.value], 
                     item[MapsColumns.LONGITUDE.value], item[MapsColumns.SOURCE_URL.value])
                )
                map_id = cur.fetchone()[0]

                # shop INSERT
                cur.execute(
                    f"INSERT INTO shop ({ShopColumns.MAP_ID.value}, category_cd, {ShopColumns.RATING.value}, {ShopColumns.KEYWORDS.value}) "
                    "VALUES (%s, %s, %s, %s) RETURNING shop_id",
                    (map_id, item["food_category_cd"], item[ShopColumns.RATING.value], item[ShopColumns.KEYWORDS.value])
                )
                shop_id = cur.fetchone()[0]

                # menus
                self._load_menus(cur, shop_id, item["menus_json"])
                return True
            except Exception as e:
                logger.error(f"!!! DB 적재 실패 ({item.get('name')}): {e}")
                return False
        
        return self.db.execute_transaction(task)

    def _load_menus(self, cur, shop_id: int, menus_json: str):
        try:
            m_list = json.loads(menus_json)
            for m in m_list:
                name = str(m.get("menu_name", "")).strip()[:100]
                price = self.processor.safe_int(m.get("menu_price"))
                if name:
                    cur.execute(f"INSERT INTO menu (shop_id, {MenuColumns.NAME.value}, {MenuColumns.PRICE.value}) VALUES (%s, %s, %s)",
                                (shop_id, name, price))
        except: pass
