import sqlalchemy
from src.core.repository.database import db_manager

def check_db():
    try:
        engine = db_manager.engine
        with engine.connect() as conn:
            count = conn.execute(sqlalchemy.text('SELECT count(*) FROM "codeT"')).scalar()
            print(f"Total rows in codeT: {count}")
            
            # Sample data
            rows = conn.execute(sqlalchemy.text('SELECT cd, name FROM "codeT" LIMIT 5')).mappings().all()
            for r in rows:
                print(f" - {r['cd']}: {r['name']}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_db()
