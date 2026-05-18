"""AWS Lambda 핸들러 모듈(`get_reviews` → 감성 → LLM 키워드 단계별 배치).

배포 시 작업 디렉터리( zip 루트 )를 `post_analysis`로 두고,
각 함수의 핸들러는 ``lambda.<모듈명>.lambda_handler`` 형식으로 지정한다.
"""
