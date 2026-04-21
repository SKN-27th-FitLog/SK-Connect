# 패키지 
import pandas as pd

# 모듈 
from common.constant import Stage, Status
from common.utils import build_csv_path, save_csv, get_run_time



if __name__ == "__main__":

    # 실행 시간을 가져옴 
    run_time = get_run_time()

    # 테스트 용으로 빈 df를 생성 (생성을 하던 불러오던 어떤 식으로든 df를 정의하면 됨)
    df = pd.DataFrame()

    # 저장 경로 생성
    crawling_path1  = build_csv_path(Stage.CRAWLILNG, "it", Status.SUCCESS, run_time)
    crawling_path2  = build_csv_path(Stage.CRAWLILNG, "it", Status.FAIL, run_time)
    cleaning_path1  = build_csv_path(Stage.CLEANING, "it", Status.SUCCESS, run_time)
    cleaning_path2  = build_csv_path(Stage.CLEANING, "it", Status.FAIL, run_time)
    save_path1      = build_csv_path(Stage.SAVE, "it", Status.SUCCESS, run_time)
    save_path2      = build_csv_path(Stage.SAVE, "it", Status.FAIL, run_time)

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


    ###################################
    # 크롤링
    ###################################
    # 1. 크롤링은 임의의 웹 페이지에서 HTML 문서를 파싱하는 것부터 시작함 
    # 2. 기준 페이지에서 부터 한줄의 row 를 채우기 위해 행동을 반복하게 됨 
    # 3. 행동의 반복에는 Requests 라이브러리를 사용함 
    # 4. 크롤링 결과에 대해서는 beatifulsoup4 라이브러리를 사용해서 정규화 함
    # 5. 크롤링 결과에 대해 각 크롤링 대상 별로 분류하고 이를 데이터 프레임에 저장함 
    # 6. 값을 저장할 때 기계적으로 값을 가져와서 저장하도록 하고 특정 컬럼을 채우지 못했을 경우 fail 처리 한다. 
    # 7. 구체적인 파싱 전략에 대해서는 포인터 사용해서 데이터 확인해보자 
    # 8. 컬럼단계부터 스키마에 맞게 채울까>
    # 9. 댓글에 대한 처리는 어떻게 할까?
    # => 아니면 따지지 말고 그냥 수집할까? 전처리 포함해서 클린징에서 처리하는걸로 하고 무식하게 수집하면 어떻지?
    


    ###################################
    # 클린징
    ###################################
    # 스키마에 맞게 처리하는 것 까진 알겠는데 그래서 뭐하지?
    # 해당 부분에서 데이터 파싱 까지만 하고 여기서는 필요한 전처리가 있으면 처리하는 정도


    ###################################
    # 저장
    ##################################
    # 저장 파트만 따로 만들어서 함수화 한다. 
    # 저장 성공에 이르면 기존 클린징 파일을 다시 세이브 파일로 정의한다. 
    # 한번에 밀어넣을거라서 실패하면 같이 망하고 성공하면 같이 성공하게 됨)


    ###################################
    # 재시도 
    ##################################

    # 아직 잘 모르겠음 