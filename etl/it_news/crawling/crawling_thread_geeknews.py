'''
geeknews 크롤링 작업 순서
1. 기준 페이지에서 수집해야 할 게시글의 URL 주소를 리스트업 한다. 
=> 해당 리스트 업은 지정된 페이지 수 (기본 10개) 이거나 아니면 설정개수 이하에서 끝나는 경우 마지막 페이지 번호까지 진행한다. 
2. 각 게시글의 URL 주소를 리스트에 넣고 차례대로 순회하며 게시글을 크롤링 한다. 
3. 게시글 각각을 크롤링 하면 결과물로 하나의 row를 생성한다. 
4. 게시글 크롤링 할 때 댓글 내용도 같이 수집한다. => 일단 보류 
5. 게시글 내용을 파싱한다. DB에 적제해야 하는 실제 컬럼들 기준으로 적용함 (중간과정 필요 없을듯)
6. 중요한 데이터를 수집 / 파싱하는데 실패하면 해당 URL 행은 별도 실패용 DataFrame에 넣고(`error` 컬럼). 클리닝 단계의 `state`(success/fail)와는 별개다.
7. 파싱에 성공한 행만 성공용 DataFrame에 쌓는다. 이후 단계에서 날짜 워터마크로 행을 거른 뒤 CSV로 저장한다.
8. 모든 게시글 URL순회가 끝나면 success / fail 데이터 프레임 들을 지정한 경로에 csv 파일로 저장한다. 
9. 각 컬럼 데이터를 채우는 방법에 대해서는 컬럼별 상세 데이터 작업 때 정의하도록 한다. 
10. 작업 중 필요한 상수값들에 대해서는 constant.py 파일을 common 폴더에 두고 사용한다. 
'''

# 패키지
import logging
import time
from datetime import datetime
from typing import Optional, Tuple
from urllib.parse import parse_qs, urljoin, urlparse
from tqdm import tqdm

import requests
import pandas as pd
from bs4 import BeautifulSoup

# 모듈
from common.constant import CodeTable, CrawlingColumn, CrawlingConstant as C_Constant, Service
from common.crawling_http import run_crawl_and_save, user_agent_headers
from common.errors import EtlErrors
from common.utils import korean_relative_time
from postgresql.watermark import get_last_success_date

logger = logging.getLogger(__name__)

#########################################################################
# 게시글 전체 목록 주회 
#########################################################################

def get_article_list() -> list[str]:
    """geeknews 목록 페이지를 순회해 게시글 절대 URL 목록을 수집한다.

    Note:
        함수 유형: E — HTTP·HTML 파싱
        안전성: Level 3
        불변 규칙: 최대 `PAGE_COUNT` 페이지; 게시글 없으면 종료
        부작용: news.hada.io 요청
    """
    article_urls = []
    list_origin = urlparse(Service.GEEKNEWS.url)
    site_base = f"{list_origin.scheme}://{list_origin.netloc}/"

    # news.hada.io 목록은 ?page=1 이 첫 페이지
    page_num = 1

    with tqdm(desc="geeknews 게시글 목록 URL 수집", unit="page") as pbar:
        # 최대 페이지 수에 도달할 때 까지 반복해서 진행한다. 
        while True:
            url = Service.GEEKNEWS.url + f"?page={page_num}"
            response = requests.get(url, headers=user_agent_headers())
            soup = BeautifulSoup(response.text, "html.parser")

            # 긱뉴스(하다) 목록: 각 행의 GN 토픽 링크는 div.topicdesc 내 a[href^='topic?id=']
            articles = soup.select("div.topic_row div.topicdesc a[href^='topic?id=']")
            # 게시글이 없으면 반복문을 종료한다.

            if not articles:
                break
            for a in tqdm(articles, desc="게시글 URL 수집(페이지 내)", unit="개", leave=False):
                href = a.get("href")
                if href:
                    article_urls.append(urljoin(site_base, href))
            pbar.update(1)
            if page_num >= C_Constant.PAGE_COUNT:
                break
            time.sleep(C_Constant.REQUEST_DELAY_SECONDS)
            page_num += 1

    return article_urls


#########################################################################
# 게시글 1개 목록에 대한 실행 함수 
#########################################################################

# 게시글 1개 soup된 내용 가지고 슬라이싱 해서 컬럼값 반환 
def parse_article(url:str) -> dict:
    """geeknews 토픽 URL 1건에서 `CrawlingColumn` dict를 추출한다.

    Note:
        함수 유형: E — HTTP·파싱
        안전성: Level 3
        불변 규칙: 필수 필드 누락·파싱 실패 시 예외 → `run_crawl_and_save` fail 행
        부작용: 게시글 HTML GET
    """

    # 게시글 1개 soup 
    response = requests.get(url, headers=user_agent_headers())
    soup = BeautifulSoup(response.text, "html.parser")

    c = CrawlingColumn
    article_dict = {
        c.TITLE.value: slicing_title(soup),
        c.CONTENT.value: slicing_content(soup),
        c.THREAD.value: slicing_thread(url),
        c.ARTICLE_URL.value: url,
        c.CREATED_AT.value: slicing_created_at(soup),
        c.VIEW_COUNT.value: C_Constant.DEFAULT_INT,  # 해당 사이트에 조회수 없음
        c.COMMENT_COUNT.value: slicing_comment_count(soup),
        c.POINT.value: slicing_point(soup),
        c.AUTHOR.value: slicing_author(soup),
        c.MAP_ID.value: None,
        c.CATEGORY_CD.value: CodeTable.CATEGORY_ETC.value,
        c.INFORMATION_CD.value: CodeTable.INFORMATION_IT.value,
        c.SHOP_CD.value: None,
    }

    return article_dict



#########################################################################
# 게시글 1개 컬럼별 슬라이싱 
#########################################################################

# 제목 슬라이싱 
def slicing_title(soup: BeautifulSoup) -> str:
    """geeknews HTML에서 제목 텍스트를 추출한다.

    Note:
        함수 유형: E — DOM 추출(soup 입력)
        안전성: Level 0 — HTTP 없음
    """

    title = soup.select_one("div.topic .topictitle h1") \
            or soup.select_one(".topictitle h1")
    
    return title.get_text(strip=True)

# 내용 슬라이싱 
def slicing_content(soup: BeautifulSoup) -> str:
    """geeknews HTML에서 본문 텍스트를 추출한다.

    Note:
        함수 유형: E — DOM 추출
        안전성: Level 0
    """

    # 본문: topic.js 렌더 영역 — id=topic_contents
    content = soup.select_one("#topic_contents") \
            or soup.select_one("div.topic_contents")

    return content.get_text("\n", strip=True)

# 게시글 id 슬라이싱
def slicing_thread(article_url: str) -> str:
    """URL `topic?id=` 값에 `geeknews_` 접두를 붙인 `thread`를 만든다.

    Note:
        함수 유형: A — URL 파싱
        안전성: Level 0
        불변 규칙: id 없으면 예외
    """
    # geeknews_1234 형식으로 고유 id 값을 가지도록 처리함 
    return f"{Service.GEEKNEWS.service}_{parse_qs(urlparse(article_url).query)['id'][0]}"

# 작성일자 슬라이싱
def slicing_created_at(soup: BeautifulSoup) -> Optional[datetime]:
    """topicinfo 상대 시각(예: 8시간전)을 `korean_relative_time`으로 datetime화한다.

    Note:
        함수 유형: E — DOM + A(시간 변환)
        안전성: Level 0
        불변 규칙: 미발견 시 `EtlErrors.Crawl.created_at_not_found` 예외
    """
    topicinfo = soup.select_one("div.topicinfo")

    # topicinfo 내 span 태그 내 텍스트를 차례대로 추출 
    # korean_relative_time 함수를 사용해 datetime으로 변환
    for span in topicinfo.find_all("span"):
        text = span.get_text(strip=True)
        dt = korean_relative_time(text)
        if dt is not None: 
            return dt

    # 모든 span을 순회했는데도 작성일자를 찾을 수 없으면 예외 발생 
    raise ValueError(EtlErrors.Crawl.created_at_not_found())


# 댓글 수 슬라이싱
def slicing_comment_count(soup: BeautifulSoup) -> int:
    """댓글 수 DOM 속성을 정수로 반환한다.

    Note:
        함수 유형: E — DOM 추출
        안전성: Level 0
        불변 규칙: 없음·변환 실패 시 `DEFAULT_INT`
    """
    try:
        return int(soup.select_one("a[data-topic-comment-count]")["data-topic-comment-count"])
    except (TypeError, KeyError, ValueError):
        return C_Constant.DEFAULT_INT


# 점수/좋아요 수 슬라이싱
def slicing_point(soup: BeautifulSoup) -> int:
    """topicinfo에서 추천(P) 점수를 정수로 반환한다.

    Note:
        함수 유형: E — DOM 추출
        안전성: Level 0
        불변 규칙: 비숫자 시 `DEFAULT_INT`
    """
    t = soup.select_one("div.topicinfo span[id^='tp']").get_text(strip=True)
    return int(t) if t.isdigit() else C_Constant.DEFAULT_INT


# 작성자 슬라이싱
def slicing_author(soup: BeautifulSoup) -> str:
    """topicinfo `/@username` 링크에서 작성자명을 추출한다.

    Note:
        함수 유형: E — DOM 추출
        안전성: Level 0
        불변 규칙: DOM 없으면 예외
    """
    # 작성자 이름이 들어있는 부분 pick > href 부분의 값을 추출 
    href = soup.select_one('div.topicinfo a[href^="/@"]')["href"]
    return href.strip().removeprefix("/@") # 추출 값에서 앞부분 제거 



#########################################################################
# 전체 실행함수 
#########################################################################
def crawling_thread_geeknews(
    run_time: Optional[datetime] = None,
    last_created_at: Optional[object] = None,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """geeknews 크롤 단계 진입: 목록 수집 후 `run_crawl_and_save`로 raw CSV 저장.

    Note:
        함수 유형: F — 사이트별 크롤 진입
        안전성: Level 2 — CSV 쓰기; 내부 HTTP는 L3
        부작용: `process=raw` success/fail CSV
    """
    return run_crawl_and_save(
        service=Service.GEEKNEWS,
        article_urls=get_article_list(),
        parse_article=parse_article,
        tqdm_desc="geeknews 게시글 파싱",
        run_time=run_time,
        last_created_at=last_created_at,
    )




##############################################
# 내부 직접 실행 
##############################################
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    last_success_date = get_last_success_date(Service.GEEKNEWS)

    df_ok, df_bad = crawling_thread_geeknews(last_created_at=last_success_date)
    logger.info(
        "crawling done: success=%s rows, fail=%s rows",
        len(df_ok),
        len(df_bad),
    )



