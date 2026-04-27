from common.merge_utils import apply_merge_rules
from common.logging_config import set_logging
from common.connection import Connection

logger = set_logging()



class GetCrawlingData():
    def __init__(self):
        self.BATCH_SIZE = 100
        self.CATEGORY_CD = {
            "IC01": "casual", #food
            "IC02": "formal", #IT
        }

    def merge_data(self, row: dict, another_data: list[dict]) -> list[dict]:
        """각 4개의 테이블에서 가져온 데이터들을 crawling_id를 기준으로 하나의 데이터로 합친다"""
        try:
            return apply_merge_rules(row, another_data)
        except Exception as e:
            logger.error(f"Error={e}")
            return None


    def execute_query(self, query: str, params: list) -> list[dict]:
        """쿼리 실행 후 결과를 딕셔너리 리스트로 반환"""
        try:
            with Connection().get_connection().cursor() as cursor:
                cursor.execute(query, params)
                columns = [col[0] for col in cursor.description]
                rows = cursor.fetchall()
            return [dict(zip(columns, row)) for row in rows]
            
        except Exception as e:
            logger.error(f"Error={e}") #crawling_id를 함께 로깅
            Connection().get_connection().rollback()
            return None

    def route_crawling_data(self, data: list[dict]):
        """row별 category_cd에 따라 분기해 데이터를 반환"""
        try:
            for row in data:
                pass
        except Exception as e:
            logger.error(f"Error={e}")
            return None

    def get_crawling_data(self):
        """crawling 테이블에서 데이터를 조회
            동일 title+map_id 기준으로 이미 처리된 최신 crawling_id보다 큰 건만 조회"""
        query = """
            """
        rows = self.execute_query(query, params=[self.BATCH_SIZE])
        return rows

    def get_shop_crawling_data(self, category_cd: str):
        """4개의 테이블에서 crawling_id를 기준으로 하나의 데이터로 합친다."""
        query = """
        """
        try:
            another_data = self.execute_query(query, params=[category_cd, self.BATCH_SIZE])
            return another_data

        except Exception as e:
            logger.error(f"Error={e}")
            return None

