'''
geeknews 크롤링 작업 순서
1. 기준 페이지에서 수집해야 할 게시글의 URL 주소를 리스트업 한다. 
=> 해당 리스트 업은 지정된 페이지 수 (기본 10개) 이거나 아니면 설정개수 이하에서 끝나는 경우 마지막 페이지 번호까지 진행한다. 
2. 각 게시글의 URL 주소를 리스트에 넣고 차례대로 순회하며 게시글을 크롤링 한다. 
3. 게시글 각각을 크롤링 하면 결과물로 하나의 row를 생성한다. 
4. 게시글 크롤링 할 때 댓글 내용도 같이 수집한다. => 일단 보류 
5. 게시글 내용을 파싱한다. DB에 적제해야 하는 실제 컬럼들 기준으로 적용함 (중간과정 필요 없을듯)
6. 중요한 데이터를 수집 / 파싱하는데 실패하면 해당 데이터는 status=fail 로 분류해서 데이터 프레임에 추가한다. 
7. 이외의 데이터는 모두 status=success 로 분류해서 데이터 프레임에 추가한다. 
8. 모든 게시글 URL순회가 끝나면 success / fail 데이터 프레임 들을 지정한 경로에 csv 파일로 저장한다. 
9. 각 컬럼 데이터를 채우는 방법에 대해서는 컬럼별 상세 데이터 작업 때 정의하도록 한다. 
10. 작업 중 필요한 상수값들에 대해서는 constant.py 파일을 common 폴더에 두고 사용한다. 
'''

# 패키지
import time
from urllib.parse import urljoin, urlparse

import requests
import pandas as pd
from bs4 import BeautifulSoup

# 모듈
from constant import CrawlingConstant as C_Constant
from constant import PageURL as P_URL
from common.utils import get_run_time




#########################################################################
# 게시글 전체 목록 주회 
#########################################################################

def get_article_list() -> list[str]:
    '''기준 페이지에서 수집해야 할 게시글의 절대 URL 목록을 구하는 함수'''
    article_urls = []
    list_origin = urlparse(P_URL.GEEKNEWS.value)
    site_base = f"{list_origin.scheme}://{list_origin.netloc}/"

    # news.hada.io 목록은 ?page=1 이 첫 페이지
    page_num = 1

    # 최대 페이지 수에 도달할 때 까지 반복해서 진행한다. 
    while True:
        url = P_URL.GEEKNEWS.value + f"?page={page_num}"
        response = requests.get(url, headers={"User-Agent": C_Constant.USER_AGENT})
        soup = BeautifulSoup(response.text, "html.parser")

        # 긱뉴스(하다) 목록: 각 행의 GN 토픽 링크는 div.topicdesc 내 a[href^='topic?id=']
        articles = soup.select("div.topic_row div.topicdesc a[href^='topic?id=']")
        # 게시글이 없으면 반복문을 종료한다.

        if not articles:
            break
        for a in articles:
            href = a.get("href")
            if href:
                article_urls.append(urljoin(site_base, href))
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
    response = requests.get(url, headers={"User-Agent": C_Constant.USER_AGENT})
    soup = BeautifulSoup(response.text, "html.parser")

    # 각 컬럼별 슬라이싱 
    article_dict = {
        "title": slicing_title(soup),
        "content": slicing_content(soup),
        "thread": slicing_thread(soup),
        "article_url": url,                                 # 입력받은 URL 주소 그대로 반환
        "created_at": slicing_created_at(soup),
        "view_count": 0,                                    # 해당 게시글에는 글 조회수 없음 
        "comment_count": slicing_comment_count(soup),
        "point": slicing_point(soup),
        "author": slicing_author(soup),
        "map_id": 0,                                        # 해당 게시글은 위치정보 없음 
        "category_cd": "CA07"                               # 카테고리 정보글 타입으로 고정
    }

    return article_dict




#########################################################################
# 게시글 1개 컬럼별 슬라이싱 
#########################################################################

# 제목 슬라이싱 
def slicing_title(soup: BeautifulSoup) -> str:
    '''게시글 1개의 HTML 문서에서 제목을 추출하는 함수 (news.hada.io 토픽 페이지 구조)'''


    title_el = soup.select_one("div.topic .topictitle h1") or soup.select_one(".topictitle h1")

    if title_el:
        title = title_el.get_text(strip=True)
    else:
        og = soup.select_one('meta[property="og:title"]')
        title = (og.get("content") or "").strip() if og else ""

    return title

# 내용 슬라이싱 
def slicing_content(soup: BeautifulSoup) -> str:
    '''게시글 1개의 HTML 문서에서 내용을 추출하는 함수 (news.hada.io 토픽 페이지 구조)'''

    # 본문: topic.js 렌더 영역 — id=topic_contents
    content_el = soup.select_one("#topic_contents") or soup.select_one("div.topic_contents")

    if content_el:
        content = content_el.get_text("\n", strip=True)
    else:
        content = ""

    return content

# 게시글 id 슬라이싱 
def slicing_thread(soup: BeautifulSoup) -> str:
    pass

# 작성일자 슬라이싱
def slicing_created_at(soup: BeautifulSoup) -> str:
    pass

# 댓글 수 슬라이싱
def slicing_comment_count(soup: BeautifulSoup) -> str:
    pass

# 점수/좋아요 수 슬라이싱
def slicing_point(soup: BeautifulSoup) -> str:
    pass

# 작성자 슬라이싱
def slicing_author(soup: BeautifulSoup) -> str:
    pass




#########################################################################
# 전체 실행함수 
#########################################################################
def crawling_thread_geeknews(run_time:str=None):
    pass







if __name__ == "__main__":
    run_time = get_run_time()
    article_urls = get_article_list()
    article_dict = parse_article(article_urls[0])
    print(article_dict)



