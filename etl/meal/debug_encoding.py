import sqlalchemy
from src.core.repository.database import db_manager

def check_db():
    try:
        engine = db_manager.engine
        with engine.connect() as conn:
            # Check SC01 specifically
            res = conn.execute(sqlalchemy.text("SELECT cd, name FROM \"codeT\" WHERE cd = 'SC01'")).mappings().first()
            if res:
                print(f"SC01 Name: {res['name']}")
                print(f"SC01 Name Hex: {res['name'].encode('utf-8').hex()}")
            else:
                print("SC01 not found")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_db()
