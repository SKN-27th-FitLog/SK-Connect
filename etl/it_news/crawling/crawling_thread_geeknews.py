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
from common.constant import CodeTable
from common.constant import CrawlingColumn, CrawlingConstant as C_Constant, Service, Stage, Status
from common.utils import (
    build_csv_path,
    coalesce_last_created_at,
    get_last_success_date,
    get_run_time,
    korean_relative_time,
    save_csv,
)

logger = logging.getLogger(__name__)

def _user_agent_headers() -> dict[str, str]:
    return {C_Constant.USER_AGENT_HEADER: C_Constant.USER_AGENT}

#########################################################################
# 게시글 전체 목록 주회 
#########################################################################

def get_article_list() -> list[str]:
    '''기준 페이지에서 수집해야 할 게시글의 절대 URL 목록을 구하는 함수'''
    article_urls = []
    list_origin = urlparse(Service.GEEKNEWS.url)
    site_base = f"{list_origin.scheme}://{list_origin.netloc}/"

    # news.hada.io 목록은 ?page=1 이 첫 페이지
    page_num = 1

    with tqdm(desc="geeknews 게시글 목록 URL 수집", unit="page") as pbar:
        # 최대 페이지 수에 도달할 때 까지 반복해서 진행한다. 
        while True:
            url = Service.GEEKNEWS.url + f"?page={page_num}"
            response = requests.get(url, headers=_user_agent_headers())
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
    '''게시글 1개의 HTML 문서에서 필요한 데이터를 추출하는 함수 (news.hada.io 토픽 페이지 구조)'''

    # 게시글 1개 soup 
    response = requests.get(url, headers=_user_agent_headers())
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
        c.CATEGORY_CD.value: CodeTable.IT_NEWS.value,
    }

    return article_dict



#########################################################################
# 게시글 1개 컬럼별 슬라이싱 
#########################################################################

# 제목 슬라이싱 
def slicing_title(soup: BeautifulSoup) -> str:
    '''게시글 1개의 HTML 문서에서 제목을 추출하는 함수 (news.hada.io 토픽 페이지 구조)'''

    title = soup.select_one("div.topic .topictitle h1") \
            or soup.select_one(".topictitle h1")
    
    return title.get_text(strip=True)

# 내용 슬라이싱 
def slicing_content(soup: BeautifulSoup) -> str:
    '''게시글 1개의 HTML 문서에서 내용을 추출하는 함수 (news.hada.io 토픽 페이지 구조)'''

    # 본문: topic.js 렌더 영역 — id=topic_contents
    content = soup.select_one("#topic_contents") \
            or soup.select_one("div.topic_contents")

    return content.get_text("\n", strip=True)

# 게시글 id 슬라이싱
def slicing_thread(article_url: str) -> str:
    """URL 의 topic?id= 값에 geeknews_ 접두사. id 없으면 예외로 실패."""
    # geeknews_1234 형식으로 고유 id 값을 가지도록 처리함 
    return f"{Service.GEEKNEWS.service}_{parse_qs(urlparse(article_url).query)['id'][0]}"

# 작성일자 슬라이싱
def slicing_created_at(soup: BeautifulSoup) -> Optional[datetime]:
    """div.topicinfo 내 상대 시각(예: 8시간전)을 현재 시각에서 차감해 datetime으로 반환."""
    topicinfo = soup.select_one("div.topicinfo")

    # topicinfo 내 span 태그 내 텍스트를 차례대로 추출 
    # korean_relative_time 함수를 사용해 datetime으로 변환
    for span in topicinfo.find_all("span"):
        text = span.get_text(strip=True)
        dt = korean_relative_time(text)
        if dt is not None: 
            return dt

    # 모든 span을 순회했는데도 작성일자를 찾을 수 없으면 예외 발생 
    raise ValueError("작성일자를 찾을 수 없습니다.")


# 댓글 수 슬라이싱
def slicing_comment_count(soup: BeautifulSoup) -> int:
    """a[data-topic-comment-count] 정수값. 요소·속성 없음·변환 실패 시 0."""
    try:
        return int(soup.select_one("a[data-topic-comment-count]")["data-topic-comment-count"])
    except (TypeError, KeyError, ValueError):
        return C_Constant.DEFAULT_INT


# 점수/좋아요 수 슬라이싱
def slicing_point(soup: BeautifulSoup) -> int:
    """topicinfo 안 '… P by …' 구조에서 P 앞 숫자(예: id=tp12345 span 텍스트)."""
    t = soup.select_one("div.topicinfo span[id^='tp']").get_text(strip=True)
    return int(t) if t.isdigit() else C_Constant.DEFAULT_INT


# 작성자 슬라이싱
def slicing_author(soup: BeautifulSoup) -> str:
    """topicinfo 내 /@username 링크의 사용자명. DOM이 없으면 AttributeError 등으로 실패."""
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
    """게시글 URL 목록을 순회해 성공/실패 데이터프레임을 만들고 common.utils 경로에 CSV 저장."""
    if run_time is None:
        run_time = get_run_time()

    threshold = coalesce_last_created_at(last_created_at)

    article_urls = get_article_list()
    success_rows: list[dict] = []
    fail_rows: list[dict] = []

    for url in tqdm(article_urls, desc="geeknews 게시글 파싱", unit="개"):
        try:
            success_rows.append(parse_article(url))
        except Exception as e:
            c = CrawlingColumn
            fail_rows.append(
                {c.ARTICLE_URL.value: url, c.ERROR.value: str(e)}
            )
        time.sleep(C_Constant.REQUEST_DELAY_SECONDS)

    df_success = pd.DataFrame(success_rows)
    df_fail = pd.DataFrame(fail_rows)

    # 성공 데이터가 존재한다면 마지막 수집일자 기준으로 필터링 
    if success_rows:
        t = pd.Timestamp(threshold)
        ca = CrawlingColumn.CREATED_AT.value
        df_success = df_success[df_success[ca] > t].copy()

    # 저장할 데이터들이 있을 때만 파일 저장 실행 
    if not df_success.empty:
        path_success = build_csv_path(Stage.CRAWLING, CodeTable.IT_NEWS, Service.GEEKNEWS.service, Status.SUCCESS, run_time)
        save_csv(df_success, path_success)

    if not df_fail.empty:
        path_fail = build_csv_path(Stage.CRAWLING, CodeTable.IT_NEWS, Service.GEEKNEWS.service, Status.FAIL, run_time)
        save_csv(df_fail, path_fail)

    return df_success, df_fail




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



