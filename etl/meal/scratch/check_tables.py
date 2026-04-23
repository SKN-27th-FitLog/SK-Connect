import pg8000
import os
from dotenv import load_dotenv

def check_tables():
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
        cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
        tables = [row[0] for row in cur.fetchall()]
        print("Existing tables:", tables)
        cur.close()
        conn.close()
    except Exception as e:
        print("Error:", str(e))

if __name__ == "__main__":
    check_tables()
