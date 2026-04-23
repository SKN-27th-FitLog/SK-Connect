import functools
import time
from ..file_manager import logger

def trace_stage(stage_name: str):
    """
    파이프라인 각 단계(Stage)의 실행 시간과 성공 여부를 로깅하는 데코레이터입니다.
    
    적용 목적:
    - 각 Stage의 시작과 끝을 명확히 표시하여 가독성 향상
    - 실행 시간 측정을 통한 성능 모니터링
    - 발생한 예외를 캐치하여 로깅하고 다시 전파(re-raise)
    
    동작:
    1. 함수 실행 전 'Starting [Stage]' 메시지 출력
    2. 함수 실행 시간 측정
    3. 정상 종료 시 'Finished [Stage]' 메시지와 소요 시간 출력
    4. 예외 발생 시 'Error in [Stage]' 메시지와 에러 내용 출력
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            logger.info(f"===> [STAGE: {stage_name}] Starting...")
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                logger.info(f"===> [STAGE: {stage_name}] Finished successfully in {duration:.2f}s")
                return result
            except Exception as e:
                logger.error(f"!!! [STAGE: {stage_name}] Failed with error: {str(e)}")
                raise e
        return wrapper
    return decorator

def db_transaction(func):
    """
    데이터베이스 트랜잭션 처리를 위한 데코레이터입니다.
    
    적용 목적:
    - 반복되는 트랜잭션(Commit/Rollback) 로직의 모듈화 (DRY 원칙)
    - 일관된 에러 처리 및 자원 해제 보장
    
    동작:
    - 함수의 첫 번째 인자가 DBClient 객체임을 가정합니다. (self.db 등)
    - 내부적으로 execute_transaction을 호출하여 원자성을 보장합니다.
    """
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        # self.db가 DBClient 인스턴스여야 함
        if not hasattr(self, 'db'):
            raise AttributeError("Class must have a 'db' attribute (DBClient) to use @db_transaction")
        
        return self.db.execute_transaction(lambda conn, cur: func(self, conn, cur, *args, **kwargs))
    return wrapper
