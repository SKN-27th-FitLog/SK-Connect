import os
import glob
from datetime import datetime
from src.core.registry import get_repository
from src.core.storage.path_builder import HivePathBuilder

class BatchUtil:
    @staticmethod
    def resolve_batch_id(category_cd: str, targets: list, selected_targets_path: str, dt: datetime) -> tuple:
        """
        대상 셋(selected_targets_path)을 기반으로 배치 ID를 결정.
        기존에 동일 경로로 실행된 적이 있으면 해당 ID를 재사용하고 attempt를 증가시킴.
        없을 경우 신규 seq를 생성.
        """
        date_str = dt.strftime('%Y%m%d')
        meta_repo = get_repository("batch_metadata")
        
        # 1. 오늘 날짜에 동일한 target path로 실행된 기록이 있는지 확인
        existing_batch_id, next_attempt = meta_repo.find_batch_state_by_target_path(category_cd, selected_targets_path, dt)
        
        if existing_batch_id:
            # 기존 ID 재사용 및 시도 회차 저장
            meta_repo.save_batch_metadata(existing_batch_id, category_cd, selected_targets_path, next_attempt, dt)
            return existing_batch_id, next_attempt
            
        # 2. 신규 실행인 경우: 현재 날짜/카테고리의 max seq를 계산하여 다음 ID 생성
        base_path = HivePathBuilder.build_stage_base_path(
            process="raw", service="shop", category_cd=category_cd,
            stage="raw_collection", status="success", dt=dt
        )
        
        batch_dirs = glob.glob(os.path.join(base_path, "batch_id=*"))
        max_seq = 0
        for bdir in batch_dirs:
            try:
                # b_id 예: 20260424_shop_001
                b_id = os.path.basename(bdir).split("=")[-1]
                seq = int(b_id.split("_")[-1])
                if seq > max_seq:
                    max_seq = seq
            except (ValueError, IndexError):
                continue
                
        next_seq = max_seq + 1
        new_batch_id = f"{date_str}_{category_cd}_{next_seq:03d}"
        
        # 3. 신규 배치 메타데이터 저장 (첫 번째 시도)
        meta_repo.save_batch_metadata(new_batch_id, category_cd, selected_targets_path, 1, dt)
        
        return new_batch_id, 1
        
    @staticmethod
    def resolve_run_attempt(category_cd: str, batch_id: str, dt: datetime) -> int:
        """현재 배치 ID의 실행 회차를 조회"""
        meta_repo = get_repository("batch_metadata")
        return meta_repo.get_run_attempt(batch_id, category_cd, dt)

    @staticmethod
    def split_targets_into_shards(targets: list, shard_size: int) -> list[list]:
        """설계안 12장 준수 - 타겟 리스트를 shard_size 단위로 분할"""
        return [targets[i:i + shard_size] for i in range(0, len(targets), shard_size)]

    @staticmethod
    def generate_shard_id(batch_id: str, shard_index: int) -> str:
        """설계안 12장 준수 - 동일 batch 내 유일한 shard_id 생성 (예: 20260423_CA01_001_SH001)"""
        return f"{batch_id}_SH{shard_index:03d}"
