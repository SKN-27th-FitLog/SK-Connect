'''
해당 코드를 통해 나눠져 있는 테이블 들을 하나로 결합한다. 
이 때 필요한 전처리가 있다면 전처리를 적용하고 드랍해야 하는 데이터가 있다면 이것도 반영한다. 
최종적으로 나온 데이터는 DB의 스키마 데이터 양식에 맞춰서 데이터 클린징 진행되어야 합니다.

처리할 때는 최종 실행 함수가 각각의 테이블을 순회하면서 스키마 형식으로 데이터 누적
누적할 때 다른 함수가 실행하면 현재 데이터 마지막 읽어온 다음 그 아래부터 내용 갱신한다. 
내용 갱신하기 전에 컬럼에 따라 테이블 셋팅부터 진행해야 함 

'''
# 라이브러리 
import pandas as pd
from datetime import datetime


# csv 파일 로드 > for문으로 돌면서 처리하게 할 예정 
# 사용 예시: df = load_csv("sample.csv")
def load_csv(file_path):
    """
    주어진 file_path에서 CSV 파일을 읽어서 pandas DataFrame으로 반환합니다.
    """
    try:
        df = pd.read_csv(file_path)
        return df
    except Exception as error:
        print(f"CSV 파일을 읽는 도중 오류 발생: {error}")
        return None


# 클린징 완료 후 처리된 데이터 프레임을 파일로 저장하도록 만들 예정 (중간에 샘플 확인용으로도 사용 )
# 클린징 된 데이터 프레임을 입력 값으로 받아야 하고 익스포트할 파일 네임이 들어온다. 
def save_dataframe_to_csv(dataframe, filename):
    """
    주어진 pandas DataFrame을 지정한 파일명으로 CSV로 저장합니다.

    Args:
        dataframe (pd.DataFrame): 저장할 데이터프레임
        filename (str): 저장할 파일명 (예: "output.csv")
    """
    try:
        dataframe.to_csv(filename, index=False, encoding="utf-8-sig")
        print(f"{filename} 파일로 데이터프레임이 성공적으로 저장되었습니다.")
    except Exception as error:
        print(f"CSV 파일 저장 중 오류 발생: {error}")

# thread_geeknews_with_content.csv 로드해서 전처리 후 데이터 프레임에 반환
def cleaning_geeknews(df:pd.DataFrame):

    # 원본 데이터 파일 로드 (일단은 절대 경로로... 작업되고 나면 상대경로 지정하거나 파일 경로 변수로 관리)
    _geeknews  = load_csv("etl\\it_news\\01_getter_threads\\thread_geeknews_with_content.csv")

    # 원본 데이터 중에서 _geeknews['state'] == 'ok' 아니면 해당 row는 드랍
    _geeknews = _geeknews[_geeknews['state'] == 'ok']

    # 빈 데이터 프레임 준비 
    df_geeknews = pd.DataFrame()

    # 원본 데이터 중에서 수집 대상인 컬럼을 데이터프레임으로 추가 
    df_geeknews['crawling_id'] = None
    df_geeknews['title'] = _geeknews['title'].map(lambda x: x[:200]) # 최대 200자 까지만 텍스트로 잘라서 저장 
    df_geeknews['content'] = _geeknews['content'].map(lambda x: x[:4000]) # 최대 4천자 까지만 텍스트로 잘라서 저장 
    df_geeknews['thread'] = _geeknews['topic_id'].map(lambda x: f'geek_{x}') # id의 경우는 데이터 넣는 과정에서 다시 설정될 듯 하니 일단은 내부 구분용으로 
    df_geeknews['article_url'] = _geeknews['article_url'].map(lambda x: x[:5000]) # 최대 5천자 까지만 텍스트로 잘라서 저장 
    df_geeknews['created_at'] = _geeknews['posted_at']
    df_geeknews['view_count'] = 0 # 해당 스레드에는 view가 없음 
    df_geeknews['comment_count'] = _geeknews['comment_count']
    df_geeknews['point'] = _geeknews['points']
    df_geeknews['author'] = _geeknews['author_user_id']
    df_geeknews['map_id'] = None
    df_geeknews['category_cd'] = 'CA07'
    
    # df에 df_geeknews 데이터 채움 > df 데이터 마지막 row에서부터 추가 
    df = pd.concat([df, df_geeknews], ignore_index=True)

    return df


# thread_pytorch_with_content.csv 로드해서 전처리 후 데이터 프레임에 반환
def cleaning_pytorch(df:pd.DataFrame):

    # 원본 데이터 파일 로드 (일단은 절대 경로로... 작업되고 나면 상대경로 지정하거나 파일 경로 변수로 관리)
    _pytorch  = load_csv("etl\\it_news\\01_getter_threads\\thread_pytorch_with_content.csv")

    # 원본 데이터 중에서 _geeknews['state'] == 'ok' 아니면 해당 row는 드랍
    _pytorch = _pytorch[_pytorch['state'] == 'ok']

    # 빈 데이터 프레임 준비 
    df_pytorch = pd.DataFrame()

    # 원본 데이터 중에서 수집 대상인 컬럼을 데이터프레임으로 추가 
    df_pytorch['crawling_id'] = None
    df_pytorch['title'] = _pytorch['title'].map(lambda x: x[:200]) # 최대 200자 까지만 텍스트로 잘라서 저장 
    df_pytorch['content'] = _pytorch['content'].map(lambda x: x[:4000]) # 최대 4천자 까지만 텍스트로 잘라서 저장 
    df_pytorch['thread'] = _pytorch['topic_id'].map(lambda x: f'pyto_{x}') # id의 경우는 데이터 넣는 과정에서 다시 설정될 듯 하니 일단은 내부 구분용으로 
    df_pytorch['article_url'] = _pytorch['topic_url'].map(lambda x: x[:5000]) # 최대 5천자 까지만 텍스트로 잘라서 저장 
    df_pytorch['created_at'] = _pytorch['created_at']
    df_pytorch['view_count'] = _pytorch['views']
    df_pytorch['comment_count'] = _pytorch['reply_count']
    df_pytorch['point'] = 0 # 해당 테이블에 값이 없음 
    df_pytorch['author'] = _pytorch['last_poster_username']
    df_pytorch['map_id'] = None
    df_pytorch['category_cd'] = 'CA07'
    
    # df에 df_pytorch 데이터 채움 > df 데이터 마지막 row에서부터 추가 
    df = pd.concat([df, df_pytorch], ignore_index=True)


    return df

    
####################################################################################
# 함수 실행
####################################################################################
if __name__ == "__main__":

    #######################################
    # 데이터 프레임 구성
    ########################################

    # DB에서 사용할 데이터 컬럼 셋팅
    columns = [
        'crawling_id',                # int
        'title',                      # str
        'content',                    # str
        'thread',                     # str
        'article_url',                # str
        'created_at',                 # DATETIME
        'view_count',                 # int
        'comment_count',              # int
        'point',                      # float
        'author',                     # str
        'map_id',                     # int    
        'category_cd',                # str
    ]

    # pandas에서 데이터 프레임에 기본 컬럼 셋팅 
    df = pd.DataFrame(data=None, columns=columns)

    # 데이터 프레임에 geeknews 데이터 채움 (함수 호출해서 추가된 데이터 반환)
    df = cleaning_geeknews(df)

    # 데이터 프레임에 pytorch 데이터 채움
    df = cleaning_pytorch(df)


    ##############################################################
    # 파일 생성
    ##############################################################
    # 오늘 날짜 가져와서 년월일 형식으로 가공 (260408_)
    today_str = datetime.now().strftime("_%y%m%d")

    # 생성할 파일의 폴더 path (etl\\it_news\\02_cleaning_tables\\)
    _folder = 'etl\\it_news\\02_cleaning_tables\\'

    # 생성할 파일 이름 ( today_str + 'gatter_tables.csv')
    _filename = 'gatter_tables' + today_str + '.csv'

    # 최종 폴더 경로 
    _path = _folder + _filename

    # 데이터 프레임 => csv 파일 저장 (파일 생성 시 오늘 날짜 포함해서 생성? )
    save_dataframe_to_csv(df, _path)


