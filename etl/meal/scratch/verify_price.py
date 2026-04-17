import psycopg2
from dotenv import load_dotenv
import os

def check_latest_prices():
    load_dotenv()
    try:
        conn = psycopg2.connect(
            dbname=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            host=os.getenv("DB_HOST"),
            port=os.getenv("DB_PORT")
        )
        cur = conn.cursor()
        query = """
            SELECT s.shop_id, m.name, m.price 
            FROM menu m 
            JOIN shop s ON m.shop_id = s.shop_id 
            ORDER BY s.shop_id DESC 
            LIMIT 5
        """
        cur.execute(query)
        rows = cur.fetchall()
        print("\n--- [LATEST MENU PRICES] ---")
        for r in rows:
            print(f"ShopID: {r[0]} | Menu: {r[1]} | Price: {r[2]}")
        cur.close()
        conn.close()
    except Exception as e:
        print(f"DB Error: {e}")

if __name__ == "__main__":
    check_latest_prices()
