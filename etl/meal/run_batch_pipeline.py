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
    from common_utils import logger, get_project_root, get_latest_hive_file
except ImportError:
    # 폴백 로거
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("BatchPipeline")

def load_env(env_path: Path) -> None:
    """
    .env 파일에서 환경 변수를 로드합니다. (DB 접속 정보 및 카카오 API 키 등)
    """
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    parts: List[str] = line.split("=", 1)
                    if len(parts) == 2:
                        os.environ[parts[0].strip()] = parts[1].strip()

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
    """
    전체 맛집 데이터 ETL 파이프라인 오케스트레이션
    - AWS S3 호환 하이브 파티션 구조 유지
    - maps, shop, menu, crawling 테이블 간 정합성 확보
    - 카카오 API를 통한 위경도 수집 연동
    """
    base_dir: Path = Path(__file__).resolve().parent
    load_env(base_dir / ".env")

    parser = argparse.ArgumentParser(description="[To-be] 통합 맛집 ETL 배치 파이프라인")
    parser.add_argument("--targets", default=os.environ.get("TARGETS_FILE", "targets_example.csv"))
    parser.add_argument("--host", default=os.environ.get("DB_HOST", "localhost"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("DB_PORT", "5432")))
    parser.add_argument("--dbname", default=os.environ.get("SERVICE_DB_NAME", "service"))
    parser.add_argument("--user", default=os.environ.get("DB_USER", "user"))
    parser.add_argument("--password", default=os.environ.get("DB_PASSWORD", "password123"))
    parser.add_argument("--truncate-first", action="store_true")
    parser.add_argument("--headful", action="store_true")
    parser.add_argument("--limit", type=int, default=None, help="수집할 가게 개수 제한 (테스트용)")
    parser.add_argument(
        "--kakao-api-key",
        default=os.environ.get("KAKAO_API_KEY", ""),
        help="카카오 REST API 키 (위경도 조회용)",
    )
    
    args = parser.parse_args()

    # 공통 데이터베이스 설정
    db_args: List[str] = [
        "--host", args.host, "--port", str(args.port), "--dbname", args.dbname,
        "--user", args.user, "--password", args.password
    ]

    logger.info("====================================================")
    logger.info("   🚀 통합 맛집 ETL 아키텍처 배치 시작              ")
    logger.info("   구조: 하이브 파티션 유지 / DB 매핑 정교화        ")
    logger.info("====================================================")

    # --- [Stage 1] 맛집 상세 정보 트랙 (Restaurant Detail Track) ---
    
    # 1-1. Raw (Link): 가게 목록 및 링크 수집
    run_step([
        sys.executable, str(base_dir / "meal_detail" / "raw" / "collect_links.py"),
        "--targets", args.targets,
        *(["--headful"] if args.headful else [])
    ], "Detail-Raw-Links")

    # [중요 변경] 입력 소스를 'service=shop'이 아닌 'service=shop_links'에서 찾습니다.
    # 사유: 목록 데이터와 상세 데이터의 저장 경로가 겹치면 DB 적재 단계에서 잘못된 파일을 선택할 수 있기 때문입니다.
    latest_links: Optional[str] = get_latest_hive_file("process=raw", "service=shop_links")
    if not latest_links:
        logger.error("❌ 수집된 링크 정보(shop_links)가 없습니다.")
        sys.exit(1)
        
    # 1-2. Raw (Detail): 상세 정보 수집
    run_step([
        sys.executable, str(base_dir / "meal_detail" / "raw" / "collect_details.py"),
        "--input", latest_links,
        *(["--limit", str(args.limit)] if args.limit else []),
        *(["--headful"] if args.headful else [])
    ], "Detail-Raw-Details")

    # 최신 상세 raw 파일 확보
    latest_details: Optional[str] = get_latest_hive_file("process=raw", "service=shop")
    if not latest_details:
        logger.error("❌ 수집된 상세 정보 파일이 없습니다.")
        sys.exit(1)

    # 1-3. Save (Master): maps / shop / menu 테이블 적재 (카카오 API 포함)
    code_table: str = str(base_dir.parent.parent / "database" / "data" / "codeT.csv")
    run_step([
        sys.executable, str(base_dir / "meal_detail" / "save" / "upload_shop_to_db.py"),
        "--input", latest_details,
        "--code-table", code_table,
        "--kakao-api-key", args.kakao_api_key,
        *db_args,
    ], "Detail-Save-Shop-Master")

    # 1-4. Clean (Transform): 데이터 클렌징 및 코드 매핑
    run_step([
        sys.executable, str(base_dir / "meal_detail" / "clean" / "preprocess.py"),
        "--input", latest_details,
        "--code-table", code_table
    ], "Detail-Clean-Preprocess")

    # 최신 클렌징 파일 확보
    latest_cleansed: Optional[str] = get_latest_hive_file("process=cleansing", "service=shop")
    if not latest_cleansed:
        logger.error("❌ 전처리된 상세 정보 파일이 없습니다.")
        sys.exit(1)

    # 1-5. Save (Post): crawling 테이블 DB 적재 및 save 로그 생성
    run_step([
        sys.executable, str(base_dir / "meal_detail" / "save" / "upload_to_db.py"),
        "--input", latest_cleansed,
        *db_args,
        *(["--truncate-first"] if args.truncate_first else [])
    ], "Detail-Save-Crawling-Post")

    # --- [Stage 2] 리뷰 데이터 트랙 (Review Data Track) ---

    # 2-1. Raw (Review): 리뷰 전수 수집 및 이미지 다운로드
    run_step([
        sys.executable, str(base_dir / "meal_review" / "raw" / "collect_reviews.py"),
        "--input", latest_details,
        *(["--limit", str(args.limit)] if args.limit else []),
        *(["--headful"] if args.headful else [])
    ], "Review-Raw-Collection")

    # 최신 리뷰 raw 파일 확보
    latest_raw_reviews: Optional[str] = get_latest_hive_file("process=raw", "service=review")
    if not latest_raw_reviews:
        logger.error("❌ 수집된 리뷰 원본 파일이 없습니다.")
        sys.exit(1)

    # 2-2. Clean (Review): 리뷰 전처리 및 포맷 변환
    run_step([
        sys.executable, str(base_dir / "meal_review" / "clean" / "preprocess_reviews.py"),
        "--input", latest_raw_reviews
    ], "Review-Clean-Preprocess")

    # 최신 리뷰 클렌징 파일 확보
    latest_cleansed_reviews: Optional[str] = get_latest_hive_file("process=cleansing", "service=review")
    if not latest_cleansed_reviews:
        logger.error("❌ 전처리된 리뷰 파일이 없습니다.")
        sys.exit(1)

    # 2-3. Save (Review): 리뷰/이미지 DB 적재 및 save 로그 생성
    run_step([
        sys.executable, str(base_dir / "meal_review" / "save" / "upload_reviews_to_db.py"),
        "--input", latest_cleansed_reviews,
        *db_args
    ], "Review-Save-DB-And-Images")

    logger.info("\n====================================================")
    logger.info(" 🎉 모든 ETL 단계가 성공적으로 완료되었습니다!      🎉 ")
    logger.info(" 🎉 데이터 정합성 보장 및 적재 로그 확인 가능        🎉 ")
    logger.info("====================================================")

if __name__ == "__main__":
    main()
