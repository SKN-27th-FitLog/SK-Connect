import os
import shutil
from pathlib import Path
from datetime import datetime
import argparse

# 상위 디렉토리(etl/meal)를 경로에 추가하여 유틸리티 임포트 가능케 함
import sys
CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from common_utils import logger, get_project_root

def recover_failed_files(process_target: str, service_target: str) -> None:
    """
    status=fail 폴더에 있는 파일들을 해당 날짜의 status=success 폴더로 복구시킵니다.
    이후 run_batch_pipeline 실행 시 해당 파일들이 다시 수집/적재 대상이 됩니다.
    """
    root_dir = get_project_root() / process_target / service_target
    if not root_dir.exists():
        logger.warning(f"⚠️ 대상 경로가 존재하지 않습니다: {root_dir}")
        return

    # status=fail 폴더 탐색
    fail_paths = list(root_dir.glob("**/status=fail"))
    
    total_recovered = 0
    for fail_path in fail_paths:
        # 해당 fail_path의 부모는 날짜 폴더 (day=*)
        # success_path 생성 (동일 날짜 폴더 내 status=success)
        success_path = fail_path.parent / "status=success"
        success_path.mkdir(parents=True, exist_ok=True)
        
        fail_files = [f for f in fail_path.iterdir() if f.is_file()]
        for f in fail_files:
            try:
                # 파일 이동 (동일 이름 파일이 있을 경우 덮어쓰지 않고 벡업)
                dest = success_path / f.name
                if dest.exists():
                    timestamp = datetime.now().strftime("%H%M%S")
                    dest = success_path / f"{f.stem}_old_{timestamp}{f.suffix}"
                
                shutil.move(str(f), str(dest))
                logger.info(f"🚚 복구 완료: {f.name} -> {success_path.relative_to(get_project_root())}")
                total_recovered += 1
            except Exception as e:
                logger.error(f"❌ 복구 실패 ({f.name}): {e}")

    logger.info(f"✨ 총 {total_recovered}건의 실패 데이터가 복구되었습니다. 파이프라인을 다시 실행해 주세요.")

def main():
    parser = argparse.ArgumentParser(description="[Utility] 실패 데이터(status=fail) 복구 도구")
    parser.add_argument("--process", default="process=raw", help="대상 프로세스 (raw/cleansing)")
    parser.add_argument("--service", default="service=shop", help="대상 서비스 (shop/review)")
    
    args = parser.parse_args()
    
    logger.info(f"🔧 '{args.process}/{args.service}' 실패 데이터 복구를 시작합니다...")
    recover_failed_files(args.process, args.service)

if __name__ == "__main__":
    main()
