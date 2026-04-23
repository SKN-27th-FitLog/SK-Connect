import pg8000
import os
from dotenv import load_dotenv

def check_columns():
    load_dotenv()
    try:
        conn = pg8000.connect(
            host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", "5432")),
            database=os.getenv("SERVICE_DB_NAME", "service"),
            user=os.getenv("DB_USER", "user"),
            password=os.getenv("DB_PASSWORD", "password123")
        )
        cur = conn.cursor()
        # maps 테이블의 컬럼 정보 조회
        cur.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'maps'
            ORDER BY ordinal_position
        """)
        cols = [row[0] for row in cur.fetchall()]
        print("Columns in 'maps' table:", cols)
        cur.close()
        conn.close()
    except Exception as e:
        print("Error:", str(e))

if __name__ == "__main__":
    check_columns()
