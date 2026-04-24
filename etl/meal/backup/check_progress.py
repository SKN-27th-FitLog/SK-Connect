import sqlalchemy
from src.core.repository.database import db_manager

def check_full_stats():
    try:
        engine = db_manager.engine
        with engine.connect() as conn:
            maps_cnt = conn.execute(sqlalchemy.text('SELECT count(*) FROM maps')).scalar()
            shop_cnt = conn.execute(sqlalchemy.text('SELECT count(*) FROM shop')).scalar()
            crawl_cnt = conn.execute(sqlalchemy.text('SELECT count(*) FROM crawling')).scalar()
            menu_cnt = conn.execute(sqlalchemy.text('SELECT count(*) FROM menu')).scalar()
            image_cnt = conn.execute(sqlalchemy.text('SELECT count(*) FROM images')).scalar()
            
            print(f"Maps: {maps_cnt}")
            print(f"Shop: {shop_cnt}")
            print(f"Crawling: {crawl_cnt}")
            print(f"Menu: {menu_cnt}")
            print(f"Images: {image_cnt}")
            
            if maps_cnt > 0:
                print("\nSample Data (Maps):")
                rows = conn.execute(sqlalchemy.text('SELECT name, category_cd, latitude, longitude FROM maps LIMIT 3')).mappings().all()
                for r in rows:
                    print(f" - {r['name']} ({r['category_cd']}): {r['latitude']}, {r['longitude']}")

            if crawl_cnt > 0:
                print("\nSample Data (Crawling):")
                rows = conn.execute(sqlalchemy.text('SELECT author, keywords, point FROM crawling WHERE author != \'System\' LIMIT 3')).mappings().all()
                for r in rows:
                    print(f" - Author: {r['author']}, Keywords: {r['keywords']}, Point: {r['point']}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_full_stats()
