
from django.db import connection
from run import CATEGORY_CD
import time

from logging_config import set_logging
logger = set_logging()

class get_crawling_data():
    def __init__(self):
        self.BATCH_SIZE = 100

    def merge_data(self, row:dict, another_data:list[dict]) -> list[dict]:
        """각 4개의 테이블에서 가져온 데이터들을 crawling_id를 기준으로 하나의 데이터로 합친다"""
        try:
            for r in another_data:
                if r['crawling_id'] == row['crawling_id']: #crawling_id가 같은 경우
                    for key, value in r.items(): #r의 key와 value를 가져옴
                        if row.get(key) is None:
                            row[key] = value #row에 r의 key가 없으면 r의 key와 value를 추가
                    return row
                elif r['crawling_id'] != row['crawling_id']:
                    raise ValueError("crawling_id is not match")
        #예외 발생시 크롤링 id 로그 기록
        except Exception as e:
            logger.error(f"Error={e} | crawling_id={row['crawling_id']}")
            return None
        

    def cursor_excute(self, query: str, params: list)->list[dict]:
        """쿼리 실행 후 결과를 딕셔너리 리스트로 반환"""
        try:
            with connection.cursor() as cursor: #cursor 연결
                cursor.execute(query, params)
                columns = [cursor.description] #컬럼 이름 가져오기
                rows = cursor.fetchall() #데이터 가져오기
            return [dict(zip(columns,rows))] #데이터를 딕셔너리 리스트로 반환
            
        except Exception as e:
            print(f"Error: {e}")
            logger.error(f"Error={e} | crawling_id={rows['crawling_id']}") #crawling_id를 함께 로깅
            return None

    def route_crawling_data(self):
        """category_cd에 따라 분기, 데이터를 반환"""
        while True:
            try:
                #crawling테이블에서 데이터를 가져옴 + 해당 데이터의 type을 확인
                data:list[dict] = self.get_crawling_data()
                type = data[0]['category_cd']

                if type not in CATEGORY_CD: #카테고리 코드가 올바르지 않은 경우
                    raise ValueError("Invalid category_cd")

                elif type == 'IC01': #데이터가 crawling테이블과 map + shop + menu 테이블에 존재하는 경우
                    result:list[dict] = []
                    another_data = self.get_shop_crawling_data()

                    #another_data가 없는 경우
                    if another_data is None:
                        raise ValueError("another_data is None")

                    #data를 하나씩 가져오면서 another_data와 합침
                    for row in data:
                        merged_data = self.merge_data(row, another_data)  

                        if merged_data is not None:
                            result.append(merged_data)
                            return result
                        elif merged_data is None:
                            continue

                elif type == 'IC02': #crawling테이블에서만 데이터를 가져오는 경우
                    return data

            except Exception as e:
                print(f"Error: {e}")
                logger.error(f"Error={e} | crawling_id={data[0]['crawling_id']} ~ {data[-1]['crawling_id']}")
                continue

    def get_crawling_data(self):
        """crawling 테이블에서 데이터를 조회
            posts 테이블에서 crawling_id가 없는 데이터를 조회"""
        query = """
            SELECT c.*
            FROM crawling c
            WHERE c.created_at >= (
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
        rows = self.cursor_excute(query, params = [self.BATCH_SIZE])
        return rows


    def get_shop_crawling_data(self):
        """4개의 테이블에서 crawling_id를 기준으로 하나의 데이터로 합친다."""
        query = """
        SELECT m.*, c.*, s.*, menu.*
        FROM crawling c
        LEFT JOIN maps m ON c.map_id = m.map_id
        LEFT JOIN shop s ON m.map_id = s.map_id
        LEFT JOIN menu ON s.shop_id = menu.shop_id
        WHERE c.crawling_id IS NOT NULL
        """
        try:
            another_data = self.cursor_excute(query, params = ['IC01', self.BATCH_SIZE])
            return another_data[0]

        except Exception as e:
            logger.error(f"Error={e}")
            return None

