import pandas as pd

from common.constant import Stage, Status
from common.utils_path import build_csv_path
from common.utils_time import get_run_time
from common.utils_file import save_csv





if __name__ == "__main__":

    # 실행 시간을 가져옴 
    run_time = get_run_time()

    # 테스트 용으로 빈 df를 생성 (생성을 하던 불러오던 어떤 식으로든 df를 정의하면 됨)
    df = pd.DataFrame()

    # 저장 경로 생성
    crawling_path1  = build_csv_path(Stage.CRAWLILNG, "it_news", Status.SUCCESS, run_time)
    crawling_path2  = build_csv_path(Stage.CRAWLILNG, "it_news", Status.FAIL, run_time)
    cleaning_path1  = build_csv_path(Stage.CLEANING, "it_news", Status.SUCCESS, run_time)
    cleaning_path2  = build_csv_path(Stage.CLEANING, "it_news", Status.FAIL, run_time)
    save_path1      = build_csv_path(Stage.SAVE, "it_news", Status.SUCCESS, run_time)
    save_path2      = build_csv_path(Stage.SAVE, "it_news", Status.FAIL, run_time)

    # 저장
    save_csv(df, crawling_path1)
    save_csv(df, crawling_path2)
    save_csv(df, cleaning_path1)
    save_csv(df, cleaning_path2)
    save_csv(df, save_path1)
    save_csv(df, save_path2)

    print("저장 완료")

    # save의 경우는 여기서 업로드 하는 과정이 하나 더 들어감 (이외에는 차이 없음 )

    # 실패 파일들을 모아서 재적용 하는 건 어떻게 할지 이야기 필요함
    # 아마 추정컨데 실패만 모아서 실행하는게 따로 있거나
    # 아니면 실행 과정에서 실패 파일도 모아서 같이 처리하는 식으로 구성하거나 일것임 
    # 로드하는 과정에서 같이 로드한 다음 concat 하거나 별도로 다시 로드해서 처리하는 등...... 

    # 이런 경우 실패가 각 단계별로 중복해서 쌓이는데 중복 케이스 등 예외 처리를 어떻게 할지는 따로 생각해 봐야 함 
