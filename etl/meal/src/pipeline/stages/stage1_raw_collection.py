import os
import asyncio
import logging
from typing import List, Dict, Any
from datetime import datetime

from src.pipeline.stages.base_stage import BaseStage
from src.collectors.base_collector import BaseCollector
from src.core.storage.path_builder import HivePathBuilder
from src.core.storage.jsonl_writer import JsonlWriter
from src.core.policy.reason_code import ReasonCode

class Stage1RawCollection(BaseStage):
    """
    설계안 11, 12, 18장 준수 - Raw 데이터 수집 Stage.
    Discovery(검색)와 Collection(수집)을 통합 처리.
    """
    NAME = "raw_collection"

    def __init__(self, collector: BaseCollector, shard_size: int = 10):
        super().__init__(self.NAME)
        self.collector = collector
        self.shard_size = shard_size

    def _create_shards(self, targets: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        return [targets[i:i + self.shard_size] for i in range(0, len(targets), self.shard_size)]

    async def _collect_single_url(self, url: str, target_id: str, batch_id: str, category_cd: str, shard_id: str, dt: datetime) -> Dict[str, Any]:
        """단일 URL 수집 및 저장"""
        try:
            raw_data = await self.collector.collect(url)
            
            success_path = HivePathBuilder.build_path(
                process="raw", service="shop", category_cd=category_cd,
                stage=self.stage_name, batch_id=batch_id, status="success", dt=dt
            )
            filename = HivePathBuilder.build_filename(extension="html", dt=dt)
            os.makedirs(success_path, exist_ok=True)
            full_file_path = os.path.join(success_path, filename)
            
            with open(full_file_path, "w", encoding="utf-8") as f:
                f.write(raw_data["raw_content"])
            
            return {
                "entity_id": target_id,
                "entity_ref": {"target_id": target_id, "url": url, "shard_id": shard_id},
                "raw_file_path": full_file_path,
                "photo_data": raw_data.get("photo_data"),
                "status": "success",
                "collected_at": dt.isoformat()
            }
        except Exception as e:
            self.logger.warning(f"Failed to collect {url}: {e}")
            return {
                "entity_id": target_id,
                "entity_ref": {"target_id": target_id, "url": url, "shard_id": shard_id},
                "status": "fail",
                "reason_code": getattr(e, 'reason_code', ReasonCode.UNKNOWN_ERROR).name,
                "detail": str(e),
                "collected_at": dt.isoformat()
            }

    async def execute_shard(
        self, shard_targets: List[Dict[str, Any]], batch_id: str, category_cd: str, shard_id: str
    ) -> List[Dict[str, Any]]:
        results = []
        now = datetime.now()
        
        for target in shard_targets:
            # 1. Discovery 확인
            search_query = target.get('search_query')
            if search_query and hasattr(self.collector, 'discover_stores'):
                urls = await self.collector.discover_stores(search_query)
                for url in urls:
                    res = await self._collect_single_url(
                        url, target.get('address_cd'), batch_id, category_cd, shard_id, now
                    )
                    results.append(res)
            
            # 2. 직접 URL 수집
            elif target.get('url'):
                res = await self._collect_single_url(
                    target['url'], target.get('target_id', 'unknown'), batch_id, category_cd, shard_id, now
                )
                results.append(res)

        metadata_path = HivePathBuilder.build_path(
            process="raw", service="shop", category_cd=category_cd,
            stage=self.stage_name, batch_id=batch_id, status="metadata", dt=now
        )
        metadata_filename = f"shard_{shard_id}.jsonl"
        JsonlWriter.write(metadata_path, metadata_filename, results)
        return results

    async def execute(self, targets: List[Dict[str, Any]], batch_id: str, category_cd: str) -> List[Dict[str, Any]]:
        shards = self._create_shards(targets)
        all_results = []
        sem = asyncio.Semaphore(3)

        async def _run_shard_with_limit(shard_id: str, shard_data: List[Dict[str, Any]]):
            async with sem:
                return await self.execute_shard(shard_data, batch_id, category_cd, shard_id)

        tasks = [
            _run_shard_with_limit(f"{i:03d}", shard) 
            for i, shard in enumerate(shards)
        ]
        
        self.logger.info(f"Starting parallel execution for {len(shards)} shards (limit=3)...")
        shard_results_list = await asyncio.gather(*tasks)
        
        for shard_res in shard_results_list:
            all_results.extend(shard_res)
            
        return all_results
