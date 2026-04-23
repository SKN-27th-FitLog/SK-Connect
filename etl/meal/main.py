import os
import argparse
from dotenv import load_dotenv
from src.pipeline.orchestrator_v4 import OrchestratorV4

load_dotenv()

def main():
    parser = argparse.ArgumentParser(description="SK-Connect Meal ETL Orchestrator")
    parser.add_argument("--category", type=str, default="CA01", help="Category code to crawl (default: CA01)")
    parser.add_argument("--goal", type=int, default=10, help="Goal success count for this batch (default: 10)")
    
    args = parser.parse_args()

    # DB 및 수집 설정 (환경변수 기반)
    config = {
        "db_params": {
            "dbname": os.environ.get("SERVICE_DB_NAME", "service"),
            "user": os.environ.get("DB_USER", "user"),
            "password": os.environ.get("DB_PASSWORD", "password123"),
            "host": os.environ.get("DB_HOST", "localhost"),
            "port": os.environ.get("DB_PORT", "5432")
        },
        "collector_config": {
            "timeout": 60000
        }
    }

    orchestrator = OrchestratorV4(config)
    
    print(f"--- Starting Automatic Batch Run for Category: {args.category}, Goal: {args.goal} ---")
    orchestrator.run_daily_batch(category_cd=args.category, goal_count=args.goal)
    print("--- Batch Run Completed ---")

if __name__ == "__main__":
    main()
