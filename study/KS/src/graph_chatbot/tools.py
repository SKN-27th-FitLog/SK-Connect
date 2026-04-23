from langchain.tools import tool
from src.utils.constants import TavilySearch_NM


################################################################################
# tools 
################################################################################

# 날씨 정보 검색 tool 
@tool  
def search_weather_info(city: str) -> str:
    """특정 도시의 현재 날씨 정보를 검색합니다."""
    try:
        search_query = f"{city} 현재 날씨 기온"
        result_weather = TavilySearch_NM.search_weather.value[1].invoke(search_query)
        
        if not result_weather['answer'] or len(result_weather['results']) < 1:
            return f"'{city}'의 날씨 정보를 찾을 수 없습니다."
        
        # 첫 번째 결과에서 날씨 정보 추출
        weather_info = f"""
        {city} 날씨 정보:
        {result_weather['answer']}

        출처: {result_weather['results'][0]['url']}
        """
        
        return weather_info
        
    except Exception as e:
        return f"날씨 정보 검색 중 오류가 발생했습니다: {str(e)}"

# 뉴스 검색 요약 tool 
@tool
def summarize_news(topic: str) -> str:
    """특정 주제의 최신 뉴스를 검색하고 요약합니다."""
    try:
        # 검색 쿼리 생성
        search_query = f"{topic} 최신 뉴스 한국"
        
        # 검색 실행
        result_new = TavilySearch_NM.search_new.value[1].invoke(search_query)
        
        if not result_new['results']:
            return f"'{topic}'에 대한 뉴스를 찾을 수 없습니다."
        
        # 결과 요약
        summary = f"'{topic}' 관련 최신 뉴스 요약:\n\n"
        for i, result in enumerate(result_new['results'][:3], 1):
            title = result.get('title', '제목 없음')
            content = result.get('content', '내용 없음')
            url = result.get('url', '')
            
            summary += f"{i}. {title}\n"
            summary += f"   {content[:100]}...\n"
            summary += f"   {url}\n\n"
        
        return summary
        
    except Exception as e:
        return f"뉴스 검색 중 오류가 발생했습니다: {str(e)}"

# 주식 정보 검색 tool 
@tool
def search_stock_info(stock_name: str) -> str:
    """특정 주식의 현재 가격과 정보를 검색합니다."""
    try:
        search_query = f"{stock_name} 주식 현재가 주가"
        result_finance = TavilySearch_NM.search_finance.value[1].invoke(search_query)

        if not result_finance['answer'] or len(result_finance['results']) < 1:
            return f"'{stock_name}' 주식 정보를 찾을 수 없습니다."
        # 
        
        # 첫 번째 결과에서 날씨 정보 추출
        stock_info = f"""
        # {stock_name} 주식 정보:
        {result_finance['answer']}

        출처: {result_finance['results'][0]['url']}
        """
        return stock_info
        
    except Exception as e:
        return f"주식 정보 검색 중 오류가 발생했습니다: {str(e)}"