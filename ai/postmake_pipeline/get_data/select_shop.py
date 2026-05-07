from common.logging_config import set_logging
import time
logger = set_logging()

def select_shop(shop_data:list[dict])->bool:
    """
    긍정 댓글 수/ 음식점별 전체 댓글 수
    => 해당 값이 0.7 이상인 음식점 선별
    """
    try:
        positive_count = 0
        total_count = 0
        for shop in shop_data:
            if shop['sentimental'] == 'positive':
                positive_count += 1
            total_count += 1
        if positive_count / total_count >= 0.7:
            return True
        elif positive_count / total_count < 0.7:
            return False
    except Exception as e:
        logger.error(f"select_shop | Error={e} | time={time.time()} | crawling_id={shop.get('crawling_id')}")
        return False

def select_keyword(shop_data:list[dict])->list:
    """
    긍정 키워드 별 수 / 긍정 댓글 수 
    => 해당 값이 0.5 이상인 키워드만 추출
    """
    try:
        keyword_data = []
        positive_keyword_count = {}
        result_keyword = []
        for shop in shop_data:
            keywords = shop.get('positive_kw') or ''
            if isinstance(keywords, str):
                keyword_data.append([kw.strip() for kw in keywords.split('#') if kw.strip()])
            else:
                keyword_data.append(keywords)

        for keyword in keyword_data:
            for kw in keyword:
                if kw in positive_keyword_count:
                    positive_keyword_count[kw] += 1
                elif kw not in positive_keyword_count:
                    positive_keyword_count[kw] = 1
        for kw, count in positive_keyword_count.items():
            if count / len(keyword_data) >= 0.5:
                result_keyword.append(kw)
        return result_keyword
    except Exception as e:
        logger.error(f"select_keyword | Error={e} | time={time.time()} | crawling_id={shop.get('crawling_id')}")
        return []
