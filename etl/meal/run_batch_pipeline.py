import os
import argparse
import subprocess
import sys
import logging
from pathlib import Path
from typing import List, Dict, Final, Optional

# 상위 유틸리티 임포트
CURRENT_DIR: Final[Path] = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.append(str(CURRENT_DIR))

try:
    from common_utils import logger, get_project_root
except ImportError:
    # 폴백 로거
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("BatchPipeline")

def load_env(env_path: Path) -> None:
    """
    .env 파일에서 환경 변수를 로드합니다.
    """
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    parts: List[str] = line.split("=", 1)
                    if len(parts) == 2:
                        os.environ[parts[0].strip()] = parts[1].strip()

def find_latest_hive_file(process: str, service: str, status: str = "success") -> Optional[str]:
    """
    Hive 구조 내에서 가장 최신 날짜/시간의 파일을 찾아 반환합니다.
    구조: {process}/{service}/year=*/month=*/day=*/status={status}/*.csv
    """
    root: Path = get_project_root() / process / service
    if not root.exists():
        return None
    
    # 모든 CSV 파일을 찾아 정렬 (날짜/시간 계층 구조이므로 문자열 정렬이 시간순과 유사)
    files: List[Path] = sorted(root.glob(f"**/*status={status}/*.csv"), reverse=True)
    return str(files[0]) if files else None

def run_step(cmd: List[str], step_name: str) -> str:
    """
    파이프라인 단계 실행 및 로그 관리
    """
    logger.info(f"\n--- [STEP: {step_name}] ---")
    logger.info(f"실행 명령어: {' '.join(cmd)}")
    
    result = subprocess.run(cmd)
    if result.returncode != 0:
        logger.error(f"❌ '{step_name}' 단계에서 오류가 발생했습니다. (Return Code: {result.returncode})")
        sys.exit(result.returncode)
    
    logger.info(f"✅ '{step_name}' 완료.")
    return "ok"

def main() -> None:
    base_dir: Path = Path(__file__).resolve().parent
    load_env(base_dir / ".env")

    parser = argparse.ArgumentParser(description="[Next-Gen] Stage-based ETL Batch Pipeline")
    parser.add_argument("--targets", default=os.environ.get("TARGETS_FILE", "targets_example.csv"))
    parser.add_argument("--host", default=os.environ.get("DB_HOST", "localhost"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("DB_PORT", "5432")))
    parser.add_argument("--dbname", default=os.environ.get("SERVICE_DB_NAME", "service"))
    parser.add_argument("--user", default=os.environ.get("DB_USER", "user"))
    parser.add_argument("--password", default=os.environ.get("DB_PASSWORD", "password123"))
    parser.add_argument("--truncate-first", action="store_true")
    parser.add_argument("--headful", action="store_true")
    
    args = parser.parse_args()

    # 공통 데이터베이스 설정 (Any 차단)
    db_args: List[str] = [
        "--host", args.host, "--port", str(args.port), "--dbname", args.dbname,
        "--user", args.user, "--password", args.password
    ]

    logger.info("====================================================")
    logger.info("   [Next-Gen] ETL ARCHITECTURE BATCH STARTING       ")
    logger.info("   Pattern: Stage-based Isolation (Raw/Clean/Save)  ")
    logger.info("====================================================")

    # --- [Stage 1] 맛집 상세 정보 수집 (Restaurant Detail) ---
    
    # 1-1. Raw: Link Collection
    run_step([
        sys.executable, str(base_dir / "meal_detail" / "raw" / "collect_links.py"),
        "--targets", args.targets,
        *(["--headful"] if args.headful else [])
    ], "Detail-Raw-Links")

    # 1-2. Raw: Detail Collection (Latest raw link file 필요)
    latest_links: Optional[str] = find_latest_hive_file("process=raw", "service=shop")
    if not latest_links:
        logger.error("수집된 링크 정보가 없습니다.")
        sys.exit(1)
        
    run_step([
        sys.executable, str(base_dir / "meal_detail" / "raw" / "collect_details.py"),
        "--input", latest_links,
        *(["--headful"] if args.headful else [])
    ], "Detail-Raw-Details")

    # 1-3. Clean: Preprocessing (Latest raw detail file 필요)
    latest_details: Optional[str] = find_latest_hive_file("process=raw", "service=shop")
    code_table: str = str(base_dir.parent.parent / "database" / "data" / "codeT.csv") # 호출자가 맞춰야 함
    
    run_step([
        sys.executable, str(base_dir / "meal_detail" / "clean" / "preprocess.py"),
        "--input", latest_details,
        "--code-table", code_table
    ], "Detail-Clean-Preprocess")

    # 1-4. Save: Database Ingestion (Latest cleansing file 필요)
    latest_cleansed: Optional[str] = find_latest_hive_file("process=cleansing", "service=shop")
    run_step([
        sys.executable, str(base_dir / "meal_detail" / "save" / "upload_to_db.py"),
        "--input", latest_cleansed,
        *db_args,
        *(["--truncate-first"] if args.truncate_first else [])
    ], "Detail-Save-DB")

    # --- [Stage 2] 리뷰 데이터 수집 (Review Data) ---

    # 2-1. Raw: Review Collection (Latest detailing raw file로부터 식당 목록 활용)
    run_step([
        sys.executable, str(base_dir / "meal_review" / "raw" / "collect_reviews.py"),
        "--input", latest_details,
        *(["--headful"] if args.headful else [])
    ], "Review-Raw-Collection")

    # 2-2. Clean: Review Preprocessing
    latest_raw_reviews: Optional[str] = find_latest_hive_file("process=raw", "service=review")
    run_step([
        sys.executable, str(base_dir / "meal_review" / "clean" / "preprocess_reviews.py"),
        "--input", latest_raw_reviews
    ], "Review-Clean-Preprocess")

    # 2-3. Save: Review DB Ingestion
    latest_cleansed_reviews: Optional[str] = find_latest_hive_file("process=cleansing", "service=review")
    run_step([
        sys.executable, str(base_dir / "meal_review" / "save" / "upload_reviews_to_db.py"),
        "--input", latest_cleansed_reviews,
        *db_args
    ], "Review-Save-DB")

    logger.info("\n====================================================")
    logger.info(" 🎉 All ETL architecture stages completed!       🎉 ")
    logger.info("====================================================")

if __name__ == "__main__":
    main()
