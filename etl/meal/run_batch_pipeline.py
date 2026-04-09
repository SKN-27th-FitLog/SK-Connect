import os
import argparse
import subprocess
import sys
from pathlib import Path

def load_env(env_path: Path) -> None:
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    parts = line.split("=", 1)
                    if len(parts) == 2:
                        os.environ[parts[0].strip()] = parts[1].strip()

def run_step(cmd: list) -> None:
    print(f"\n🚀 실행 중: {' '.join(cmd)}")
    result = subprocess.run(cmd)
    if result.returncode != 0:
        print(f"❌ 에러 발생 스텝: {' '.join(cmd)}")
        print("전체 파이프라인(배치)을 중단합니다.")
        sys.exit(result.returncode)

def main():
    base_dir = Path(__file__).resolve().parent
    load_env(base_dir / ".env")

    parser = argparse.ArgumentParser(description="맛집 상세 및 리뷰 전체 파이프라인 배치 실행")
    parser.add_argument("--targets", default=os.environ.get("TARGETS_FILE", "targets_example.csv"), help="맛집 지역/분류 타겟 CSV")
    parser.add_argument("--host", default=os.environ.get("DB_HOST", "localhost"), help="DB Host")
    parser.add_argument("--port", type=int, default=int(os.environ.get("DB_PORT", "5432")), help="DB Port")
    parser.add_argument("--dbname", default=os.environ.get("DB_NAME", "mydb"), help="DB Name")
    parser.add_argument("--user", default=os.environ.get("DB_USER", "myuser"), help="DB User")
    parser.add_argument("--password", default=os.environ.get("DB_PASS", "mypw"), help="DB Password")
    parser.add_argument("--kakao-api-key", default=os.environ.get("KAKAO_API_KEY", ""), help="카카오 REST API 키 (위경도 수집용)")
    parser.add_argument("--truncate-first", action="store_true", help="수집된 데이터를 DB에 삽입 전 기존 데이터를 초기화")
    parser.add_argument("--headful", action="store_true", help="크롤링 시 브라우저 표시")
    
    args = parser.parse_args()

    # 파이프라인 1. 맛집 상세 정보 수집 (meal_detail)
    meal_detail_dir = base_dir / "meal_detail"
    
    cmd_01_detail = [sys.executable, str(meal_detail_dir / "01_collect_store_links.py"), "--targets", args.targets]
    if args.headful:
        cmd_01_detail.append("--headful")
        
    cmd_02_detail = [sys.executable, str(meal_detail_dir / "02_collect_store_details.py")]
    if args.headful:
        cmd_02_detail.append("--headful")
        
    cmd_03_detail = [
        sys.executable, str(meal_detail_dir / "03_preprocess_and_upload.py"),
        "--host", args.host,
        "--port", str(args.port),
        "--dbname", args.dbname,
        "--user", args.user,
        "--password", args.password,
        "--kakao-api-key", args.kakao_api_key
    ]
    if args.truncate_first:
        cmd_03_detail.append("--truncate-first")

    # 파이프라인 2. 다이닝코드 리뷰 수집 (meal_review)
    meal_review_dir = base_dir / "meal_review"
    
    cmd_02_review = [sys.executable, str(meal_review_dir / "02_collect_store_reviews.py")]
    if args.headful:
        cmd_02_review.append("--headful")
        
    cmd_03_review = [
        sys.executable, str(meal_review_dir / "03_preprocess_and_upload_reviews.py"),
        "--host", args.host,
        "--port", str(args.port),
        "--dbname", args.dbname,
        "--user", args.user,
        "--password", args.password
    ]
    # Note: truncate-first is omitted for reviews to avoid dropping user generated content safely, 
    # but passed if requested.
    if args.truncate_first:
        cmd_03_review.append("--truncate-first")

    # 실행 절차
    print("====================================")
    print("   ETL BATCH PIPELINE STARTING      ")
    print("====================================")
    
    run_step(cmd_01_detail)
    run_step(cmd_02_detail)
    run_step(cmd_03_detail)
    
    run_step(cmd_02_review)
    run_step(cmd_03_review)
    
    print("====================================")
    print(" 🎉 모든 파이프라인 배치가 완료되었습니다! 🎉 ")
    print("====================================")

if __name__ == "__main__":
    main()
