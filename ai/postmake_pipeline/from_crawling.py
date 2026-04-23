
from django.db import connection



class get_crawling_data():
    def __init__(self, category_cd: str):
        self.category_cd = category_cd
        self.BATCH_SIZE = 100

    def merge_data(self) -> list[dict]:
        #각 4개의 테이블에서 가져온 데이터들을 crawling_id를 기준으로 하나의 데이터로 합친다
        result = {}
        pass

        return result

    def cursor_excute(query: str, params: list)->list[dict]:
        # 쿼리 실행 후 결과를 딕셔너리 리스트로 반환
        with connection.cursor() as cursor:
            cursor.execute(query, params)
            columns = [col[0] for col in cursor.description]
            rows = cursor.fetchall()
        return [dict(zip(columns, row)) for row in rows]


    def get_info_crawling_data(self):
        query = """
            SELECT c.*
            FROM crawling c
            WHERE c.category_cd = %s
            AND c.created_at >= (
                SELECT MAX(p.created_at)
                FROM posts p
            )
            AND c.crawling_id IS NOT NULL
            AND NOT EXISTS (
                SELECT 1
                FROM posts p
                WHERE p.crawling_id = c.crawling_id
            )
            ORDER BY c.crawling_id ASC
            LIMIT %s;
            """
        rows = self.cursor_excute(query)
        while True:
            if not rows:
                print("No more data to process...")
                raise ValueError("No more data to process...")
            print(f"{len(rows)} rows to process...")


            for row in rows:
                try:
                    if row['category_cd'] == 'IC02':
                        prompt = Prompt(type='formal', data=row['content'])
                    elif row['category_cd'] == 'IC01':
                        row = self.get_shop_crawling_data()
                        prompt = Prompt(type='casual', data=row['content'])
                    elif row['category_cd'] != 'IC02' or row['category_cd'] != 'IC01':
                        raise ValueError("Invalid category_cd")

                except Exception as e:
                    print(f"Error: {e}")
                    logging.error(f"Error={e} | crawling_id={row['crawling_id']}")
                    continue

            logging.info(f"Batch {batch_count} completed...")
            print(f"Batch {batch_count} completed...")
            batch_count += 1
            time.sleep(1)

            return row


    def get_shop_crawling_data(self):
        #4개의 테이블에서 map_id를 기준으로 하나의 데이터로 합친다
        #각 maps, crawling, shop, menu 테이블에서 데이터를 가져온다
        query = """
        SELECT m.*, c.*, s.*, menu.*
        FROM maps m
        LEFT JOIN crawling c ON m.map_id = c.map_id
        LEFT JOIN shop s ON m.map_id = s.map_id
        LEFT JOIN menu ON s.shop_id = menu.shop_id
        WHERE m.category_cd = %s
        AND m.created_at >= (
            SELECT MAX(p.created_at)
            FROM posts p
        )
        """
        self.cursor_excute(query, params = ['shop', self.BATCH_SIZE])
        data = self.merge_data()

        return data
