import uuid
import os
import csv
import requests
import re
from datetime import datetime, date
from typing import List, Dict, Any, Optional

from .base_stage import BaseStage
from ..core.file_manager import logger
from ..core.utils.decorators import trace_stage
from ..db.repositories.target_repository import TargetRepository
from ..db.models.target_models import DailyTarget, SelectionPolicy
from ..core.storage.hive_path_builder import HivePathBuilder

class TargetSelection(BaseStage):
    """
    Stage 0: Daily Target Selection (Search Mode)
    정규표현식을 활용하여 동적/정적 HTML 모두에서 식당 ID를 추출합니다.
    """
    
    def __init__(self, db_client, resolver, path_builder: HivePathBuilder = None):
        super().__init__("Target Selection")
        self.db = db_client
        self.target_repo = TargetRepository(db_client)
        self.path_builder = path_builder or HivePathBuilder()
        self.keyword_file = "targets_verify_short.csv"

    @trace_stage("Target Selection")
    def run(self, category_cd: str, target_count: int = 100) -> Dict[str, Any]:
        target_data = self._execute(category_cd, target_count)
        self._save_target_meta(target_data)
        return target_data.model_dump()

    def _execute(self, category_cd: str, target_count: int) -> DailyTarget:
        today = date.today()
        batch_id = self._generate_batch_id(category_cd, today.strftime("%Y-%m-%d"))
        
        keywords = self._load_keywords_standard(category_cd)
        final_target_urls = []
        
        for kw in keywords:
            search_kw = kw.replace(category_cd, "맛집").strip()
            urls = self._search_diningcode(search_kw, limit=target_count)
            final_target_urls.extend(urls)
            if len(final_target_urls) >= target_count:
                break
        
        # 중복 제거
        try:
            loaded_urls = self.target_repo.get_already_loaded_urls(category_cd)
            final_target_urls = [url for url in final_target_urls if url not in loaded_urls]
        except Exception:
            final_target_urls = list(set(final_target_urls))

        final_target_urls = final_target_urls[:target_count]
        logger.info(f"--- [Stage 0] Selected {len(final_target_urls)} live search targets.")

        return DailyTarget(
            batch_id=batch_id,
            category_cd=category_cd,
            target_date=today,
            target_count=len(final_target_urls),
            candidate_store_ids=final_target_urls,
            selection_policy=SelectionPolicy()
        )

    def _load_keywords_standard(self, category_cd: str) -> List[str]:
        keywords = []
        try:
            if not os.path.exists(self.keyword_file):
                return ["독산동 맛집"]
            with open(self.keyword_file, mode='r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get('category') == category_cd:
                        keywords.append(f"{row.get('region', '독산동')} {category_cd}")
            return keywords if keywords else ["독산동 맛집"]
        except Exception:
            return ["독산동 맛집"]

    def _search_diningcode(self, keyword: str, limit: int) -> List[str]:
        """정규표현식을 사용하여 HTML 내의 모든 rid를 추출합니다."""
        search_urls = []
        try:
            search_url = f"https://www.diningcode.com/list.dc?query={keyword}"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            }
            resp = requests.get(search_url, headers=headers, timeout=10)
            resp.raise_for_status()
            
            # 정규표현식: rid= 다음에 오는 영숫자 조합 추출
            # 예: profile.php?rid=123asdf 또는 profile.dc?rid=... 또는 JSON 내의 "rid":"..."
            rids = re.findall(r'rid[=\":]+([a-zA-Z0-9_\-]+)', resp.text)
            
            for rid in rids:
                # 너무 짧거나 시스템 예약어인 경우 제외
                if len(rid) < 5: continue
                
                # 상세 페이지는 .php를 사용함 (확인 완료)
                full_url = f"https://www.diningcode.com/profile.php?rid={rid}"
                if full_url not in search_urls:
                    search_urls.append(full_url)
                
                if len(search_urls) >= limit:
                    break
                    
            if not search_urls:
                logger.warning(f"--- [Stage 0] No rids found in HTML for: {keyword}")
                
        except Exception as e:
            logger.error(f"!!! [Stage 0] live search failed: {e}")
        
        return search_urls

    def _save_target_meta(self, target_data: DailyTarget):
        try:
            dir_path = self.path_builder.build(stage="target_selection", status="success", dt=target_data.target_date)
            os.makedirs(dir_path, exist_ok=True)
            file_name = f"target_meta_{target_data.batch_id}.json"
            full_path = os.path.join(dir_path, file_name)
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(target_data.model_dump_json(indent=2))
        except Exception: pass

    def _generate_batch_id(self, category_cd: str, date_str: str) -> str:
        return f"{date_str.replace('-', '')}_{category_cd}_{uuid.uuid4().hex[:6].upper()}"
