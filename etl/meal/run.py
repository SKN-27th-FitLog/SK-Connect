import os
import argparse
from dotenv import load_dotenv
from src.orchestrator import ETLOrchestrator
from src.core.file_manager import logger

def main():
    # .env 파일 로드
    load_dotenv()
    
    parser = argparse.ArgumentParser(description="[v4.0 Enterprise] 통합 맛집 ETL 파이프라인")
    parser.add_argument("--targets", default=os.getenv("TARGETS_FILE", "targets_example.csv"), help="수집 대상 (region, category)")
    parser.add_argument("--limit", type=int, default=None, help="신규 수집 한도(Quota)")
    parser.add_argument("--headful", action="store_true", help="브라우저 모드 실행")
    parser.add_argument("--recovery", action="store_true", help="실패 데이터 재처리 모드 실행")
    
    args = parser.parse_args()

    # 설정 구성
    config = {
        "db_params": {
            "host": os.getenv("DB_HOST", "localhost"),
            "port": os.getenv("DB_PORT", "5432"),
            "dbname": os.getenv("SERVICE_DB_NAME", "service"),
            "user": os.getenv("DB_USER", "user"),
            "password": os.getenv("DB_PASSWORD", "password123"),
        },
        "kakao_api_key": os.getenv("KAKAO_API_KEY"),
        "code_table_path": r"C:\dev\Project\SK-Connect\database\data\codeT.csv",
        "headless": not args.headful,
        "daily_limit": args.limit or int(os.getenv("DAILY_LIMIT", 100))
    }

    try:
        orchestrator = ETLOrchestrator(config)
        
        if args.recovery:
            orchestrator.run_recovery_mode()
        else:
            orchestrator.run_full_pipeline(args.targets)
            
    except KeyboardInterrupt:
        logger.info("\n[-] 사용자에 의해 작업이 중단되었습니다.")
    except Exception as e:
        logger.error(f"!!! ETL 실행 중 실패: {e}")

if __name__ == "__main__":
    main()
