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
    # [신규] Kakao REST API 키: upload_shop_to_db.py 에서 주소 → 위경도 변환에 사용.
    # .env 의 KAKAO_API_KEY 를 우선 적용하고, 없으면 빈 문자열(위경도 0.0 저장).
    parser.add_argument(
        "--kakao-api-key",
        default=os.environ.get("KAKAO_API_KEY", ""),
        help="카카오 REST API 키 (위경도 조회용)",
    )
    
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

    # [수정] 아래 단계들에서 공통으로 사용할 최신 상세 raw 파일 경로를 먼저 확보합니다.
    # 기존에는 뒤에서 선언되어 NameError 가 발생했습니다.
    latest_details: Optional[str] = find_latest_hive_file("process=raw", "service=shop")
    if not latest_details:
        logger.error("수집된 상세 정보 파일이 없습니다.")
        sys.exit(1)

    # 1-3. [신규] Save: maps / shop / menu 테이블 적재
    # collect_details 의 raw 파일에는 메뉴/주소/평점이 포함되어 있어
    # crawling 테이블(리뷰/게시글용)과 별도로 maps/shop/menu 테이블에도
    # 적재해야 한다. 이 단계를 기존 파이프라인에 추가하여 누락을 해소.
    code_table: str = str(base_dir.parent.parent / "database" / "data" / "codeT.csv")
    run_step([
        sys.executable, str(base_dir / "meal_detail" / "save" / "upload_shop_to_db.py"),
        "--input", latest_details,
        "--code-table", code_table,
        "--kakao-api-key", args.kakao_api_key,
        *db_args,
    ], "Detail-Save-Shop")

    # 1-4. Clean: Preprocessing (Latest raw detail file 필요)
    # [수정] 위에서 정의한 latest_details 를 그대로 사용합니다.
    code_table_clean: str = str(base_dir.parent.parent / "database" / "data" / "codeT.csv")

    run_step([
        sys.executable, str(base_dir / "meal_detail" / "clean" / "preprocess.py"),
        "--input", latest_details,
        "--code-table", code_table_clean
    ], "Detail-Clean-Preprocess")

    # 1-5. Save: crawling 테이블 DB 적재 (Latest cleansing file 필요)
    latest_cleansed: Optional[str] = find_latest_hive_file("process=cleansing", "service=shop")
    run_step([
        sys.executable, str(base_dir / "meal_detail" / "save" / "upload_to_db.py"),
        "--input", latest_cleansed,
        *db_args,
        *(["--truncate-first"] if args.truncate_first else [])
    ], "Detail-Save-DB")

    # --- [Stage 2] 리뷰 데이터 수집 (Review Data) ---

    # 2-1. Raw: Review Collection
    # [수정] 상단에서 정의한 latest_details (최신 상세 raw 파일)를 사용하여
    # 해당 식당들의 리뷰를 수집합니다.
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
