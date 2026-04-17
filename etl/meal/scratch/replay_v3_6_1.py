import pandas as pd
import os
import sys
from dotenv import load_dotenv

# Ensure we can import from src
sys.path.append(os.getcwd())

from src.core.db_client import DBClient
from src.core.services.kakao_api import KakaoAPI
from src.transformers.shop_processor import ShopProcessor
from src.transformers.review_processor import ReviewProcessor
from src.loaders.shop_loader import ShopLoader
from src.loaders.post_loader import PostLoader
from src.loaders.review_loader import ReviewLoader
from src.core.file_manager import logger

def run_replay():
    load_dotenv()
    
    # 1. Config Setup (Same as run.py)
    db_params = {
        "host": os.getenv("DB_HOST", "localhost"),
        "port": os.getenv("DB_PORT", "5432"),
        "dbname": os.getenv("SERVICE_DB_NAME", "service"),
        "user": os.getenv("DB_USER", "user"),
        "password": os.getenv("DB_PASSWORD", "password123"),
    }
    kakao_api_key = os.getenv("KAKAO_API_KEY")
    code_table_path = r"C:\dev\Project\SK-Connect\database\data\codeT.csv" # Standard path

    # Files provided by user
    shop_raw_path = r"c:\dev\Project\SK-Connect\etl\meal\process=raw\service=shop\year=2026\month=04\day=17\status=success\124257.csv"
    review_raw_path = r"c:\dev\Project\SK-Connect\etl\meal\process=raw\service=review\year=2026\month=04\day=17\status=success\131012.csv"

    # Initialize components
    db_client = DBClient(db_params)
    kakao_api = KakaoAPI(kakao_api_key)
    shop_processor = ShopProcessor(code_table_path)
    
    shop_loader = ShopLoader(db_client, kakao_api, shop_processor)
    post_loader = PostLoader(db_client)
    review_processor = ReviewProcessor()
    review_loader = ReviewLoader(db_client)

    try:
        # 1. Process & Load Shops (Main data: maps, shop, menu, images)
        logger.info(f"--- [REPLAY] Loading Shop Raw: {shop_raw_path}")
        df_shop_raw = pd.read_csv(shop_raw_path)
        
        logger.info(f"--- [REPLAY] Ingesting Shops to Master Tables (Count: {len(df_shop_raw)})")
        shop_stats = shop_loader.load_all(df_shop_raw)
        logger.info(f"--- [Shop 적재 결과] 성공: {shop_stats['success']}건 | 실패(격리): {shop_stats['fail']}건")

        # 2. Process & Load Shops to Crawling (Thread='shop')
        logger.info(f"--- [REPLAY] Ingesting Shops to Crawling Table")
        df_shop_cleansed_post = shop_processor.process_batch_crawling(df_shop_raw)
        post_loader.load_all(df_shop_raw, df_shop_cleansed_post)

        # 3. Process & Load Reviews (Thread='review')
        logger.info(f"--- [REPLAY] Loading Review Raw: {review_raw_path}")
        df_review_raw = pd.read_csv(review_raw_path)
        df_review_cleansed = review_processor.process_batch(df_review_raw)
        
        logger.info(f"--- [REPLAY] Ingesting Reviews to DB (Count: {len(df_review_cleansed)})")
        review_loader.load_all(df_review_raw, df_review_cleansed)

        logger.info("============================================================")
        logger.info("--- [REPLAY] DATA RE-INGESTION COMPLETED SUCCESSFULLY ---")
        logger.info("============================================================")

    except Exception as e:
        logger.error(f"--- [REPLAY] Error during replay: {e}")
        import traceback
        traceback.print_exc()
    finally:
        pass

if __name__ == "__main__":
    run_replay()
