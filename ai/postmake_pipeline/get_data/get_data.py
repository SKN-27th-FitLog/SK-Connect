from common.logging_config import set_logging
from common.connection import get_cursor
import time
logger = set_logging()

def search_post(row:dict)->dict:
    """
    get_data로 가져온 데이터의 title을 기준으로
    post에 이미 생성된 적이 있는 가게인지 조회하고 
    생성 날짜 이후 crawling된 데이터인지 조회한다.
    """
    try:
        # post테이블에서 가져온 데이터와 동일한 title의 데이터가 있는지 확인 (가장 최근 데이터)
        query = "SELECT * FROM posts WHERE title = %s ORDER BY created_at DESC LIMIT 1"
        cursor = get_cursor(query, (row['title'],)) #post의 데이터
        data = cursor.fetchone() if cursor else None
        if not data: # 데이터
            return None
        elif data:
            return data

    except Exception as e:
        logger.error(f"search_post | Error={e} | time={time.time()}")
        return False

def get_data():
    """analysis 테이블에서 row단위로 동일한 가게의 데이터만 가져온다"""
    try:
        query = "SELECT * FROM analysis WHERE created_dt < NOW() - INTERVAL '1 day' ORDER BY title, created_dt DESC"
        cursor = get_cursor(query)
        if not cursor:
            return None
        for row in cursor.fetchall():
            post_data = search_post(row)
            if post_data and post_data['created_at'] >= row['created_dt']:
                continue
            yield row

    except Exception as e:
        logger.error(f"get_data | Error={e} | time={time.time()}")

        return None

def get_shop_data()->list[dict]:
    """get_data로 가져온 데이터"""
    try:
        shop_data:list[dict] = []
        title = ""
        data_iter = get_data()
        while True:
            data:dict = next(data_iter, None)
            if not data: # 데이터가 없으면 종료
                break
            elif title == "": # 첫 데이터 처리
                title = data['title'] 
                shop_data.append(data)
                continue
            elif title != "": # 두 번째 이후 데이터 처리
                if title != data['title']: # 동일한 가게의 데이터가 아니면 종료
                    return shop_data
                elif title == data['title']: # 동일한 가게의 데이터이면 추가
                    shop_data.append(data)
                    continue
        return shop_data
    except Exception as e:
        logger.error(f"get_shop_data | Error={e} | time={time.time()}")
        return None

def analysis_data(data:list[dict])->bool:
    try:
        count = 0
        for row in data:
            if count >= 5:
                return True
            elif row['sentimental'] == 'positive':
                count += 1
    except Exception as e:
        logger.error(f"analysis_data | Error={e} | time={time.time()}")
        return None
