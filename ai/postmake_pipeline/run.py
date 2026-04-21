from from_crawling import get_crawling_data, BATCH_SIZE
import logging

import time

logger = logging.getLogger(__name__)

def run_batch():
    batch_count = 0
    while True:
        rows = get_crawling_data(limit=BATCH_SIZE)

        if not rows:
            print("No more data to process...")
            break
        
        print(f"{len(rows)} rows to process...")

        for row in rows:
            try:
                #llm

                #push

                pass

            except Exception as e:
                print(f"Error: {e}")
                logging.error(f"Error={e} | crawling_id={row['crawling_id']}")
                continue

        logging.info(f"Batch {batch_count} completed...")
        print(f"Batch {batch_count} completed...")
        batch_count += 1
        time.sleep(1)
                
