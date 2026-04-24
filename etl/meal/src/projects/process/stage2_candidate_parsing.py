import os
import logging
from typing import List, Dict, Any
from datetime import datetime

from src.core.base_stage import BaseStage
from src.services.parsers.base_parser import BaseParser
from src.core.storage.path_builder import HivePathBuilder
from src.core.storage.jsonl_writer import JsonlWriter

class Stage2CandidateParsing(BaseStage):
    """
    [요구사항 2.2 일치] - Candidate Parsing Stage.
    Raw HTML을 읽어 구조화된 Candidate JSONL을 생성.
    """
    NAME = "candidate_parsing"

    def __init__(self, parser: BaseParser):
        super().__init__(self.NAME)
        self.parser = parser

    def execute(self, raw_metadata: List[Dict[str, Any]], batch_id: str, category_cd: str) -> List[Dict[str, Any]]:
        candidates = []
        failures = []
        now = datetime.now()
        
        for record in raw_metadata:
            if record.get("status") != "success":
                continue
                
            file_path = record.get("raw_file_path")
            if not file_path or not os.path.exists(file_path):
                continue
                
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    html = f.read()
                
                shop_data = self.parser.parse_shop(html)
                menus = self.parser.parse_menus(html)
                reviews = self.parser.parse_reviews(html)
                
                # 컬렉터가 함께 수집한 photo_data가 있으면 파서에 전달
                photo_data = record.get("photo_data")
                if photo_data and hasattr(self.parser, 'parse_images'):
                    try:
                        images = self.parser.parse_images(html, photo_data=photo_data)
                    except TypeError:
                        images = self.parser.parse_images(html)
                else:
                    images = self.parser.parse_images(html)
                
                # 2. Candidate 데이터 구성 (설계안 13번 참조)
                candidate = {
                    "entity_id": record.get("entity_id"),
                    "entity_ref": record.get("entity_ref", {}),
                    "shop": shop_data,
                    "menus": menus,
                    "reviews": reviews,
                    "images": images,
                    "parsed_at": now.isoformat()
                }
                candidates.append(candidate)
                
            except Exception as e:
                self.logger.error(f"Failed to parse {file_path}: {str(e)}")
                failures.append({
                    "entity_id": record.get("entity_id", "unknown"),
                    "entity_ref": record.get("entity_ref", {}),
                    "status": "fail",
                    "reason_code": "INVALID_DATA_FORMAT",
                    "detail": str(e),
                    "failed_at": now.isoformat()
                })
        
        if candidates:
            candidate_path = HivePathBuilder.build_path(
                process="candidate", service="shop", category_cd=category_cd,
                stage=self.stage_name, batch_id=batch_id, status="success", dt=now
            )
            filename = HivePathBuilder.build_filename(extension="jsonl", dt=now)
            JsonlWriter.write(candidate_path, filename, candidates)
            self.logger.info(f"Parsed {len(candidates)} candidates for batch {batch_id}")

        if failures:
            fail_path = HivePathBuilder.build_path(
                process="candidate", service="shop", category_cd=category_cd,
                stage=self.stage_name, batch_id=batch_id, status="fail", dt=now
            )
            filename_fail = HivePathBuilder.build_filename(extension="jsonl", dt=now)
            JsonlWriter.write(fail_path, filename_fail, failures)
        
        return candidates
