import psycopg2
from dotenv import load_dotenv
import os

def verify():
    load_dotenv()
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        dbname=os.getenv("SERVICE_DB_NAME", "service"),
        user=os.getenv("DB_USER", "user"),
        password=os.getenv("DB_PASSWORD", "password123")
    )
    cur = conn.cursor()

    print("\n" + "="*50)
    print(" [DB 적재 최종 정무 검증] ")
    print("="*50)

    # 1. 테이블별 건수 확인
    tables = ["maps", "shop", "menu", "crawling", "images"]
    for table in tables:
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        count = cur.fetchone()[0]
        print(f" - {table:<10} 건수: {count}건")

    # 2. Crawling 테이블 스레드별 확인
    cur.execute("SELECT thread, COUNT(*) FROM crawling GROUP BY thread")
    threads = cur.fetchall()
    for t, c in threads:
        print(f"   -> [Thread: {t}] 건수: {c}건")

    # 3. 최신 적재 데이터 샘플 확인 (shop)
    print("\n[최신 매장 데이터 샘플 (Shop)]")
    cur.execute("""
        SELECT s.shop_id, m.name, m.address_detail, s.rating 
        FROM shop s
        JOIN maps m ON s.map_id = m.map_id
        ORDER BY s.shop_id DESC LIMIT 1
    """)
    sample = cur.fetchone()
    if sample:
        print(f" ID: {sample[0]} | 이름: {sample[1]} | 주소: {sample[2]} | 평점: {sample[3]}")

    # 4. 최신 리뷰 및 이미지 매핑 확인
    print("\n[최신 리뷰-이미지 매핑 샘플]")
    cur.execute("""
        SELECT c.title, COUNT(i.image_id) 
        FROM crawling c
        LEFT JOIN images i ON i.table_name = 'crawling' AND i.table_id = c.crawling_id
        WHERE c.thread = 'review'
        GROUP BY c.crawling_id, c.title
        ORDER BY c.crawling_id DESC LIMIT 1
    """)
    sample_rv = cur.fetchone()
    if sample_rv:
        print(f" 리뷰대상: {sample_rv[0]} | 연결된 이미지 수: {sample_rv[1]}개")

    cur.close()
    conn.close()
    print("="*50 + "\n")

if __name__ == "__main__":
    verify()
