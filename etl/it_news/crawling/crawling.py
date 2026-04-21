'''
해당 파일에서 크롤링 실행 과정을 진행하게 된다. 
common에서 필요한 함수들을 임포트 하는 경우는 해당 파일에서 직접 실행하는 경우를 산정하고 가져오는 것이고 
실제는 해당 코드에 실행 함수 하나를 놓고 실행함수에는 설정값을 받아서 동작하도록 한다. 
실행부에는 설정값을 받아서 실행하는 식으로 한다. 
'''
from common.utils import get_run_time
from crawling_thread_geeknews import crawling_thread_geeknews
from crawling_thread_pytorch import crawling_thread_pytorch








def crawling(run_time:str=None, ):

    crawling_thread_geeknews(run_time)
    crawling_thread_pytorch(run_time)




if __name__ == "__main__":

    run_time = get_run_time()

    crawling(run_time)