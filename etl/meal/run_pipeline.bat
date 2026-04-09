@echo off
setlocal

echo ==========================================
echo Food Crawling Pipeline Batch Program
echo ==========================================

:: ---------------------------------------------------------
:: [1] 환경변수(.env) 로드
:: ---------------------------------------------------------
if exist "%~dp0.env" (
    echo [INFO] .env 파일 로딩 중...
    for /f "usebackq tokens=1,* delims==" %%A in ("%~dp0.env") do (
        set "%%A=%%B"
    )
) else (
    echo [ERROR] .env 파일이 없습니다! .env.example을 복사하여 .env를 생성하고 설정값을 입력하세요.
    pause
    exit /b 1
)

:: ---------------------------------------------------------
:: 시스템 초기화
:: ---------------------------------------------------------
:: 프로젝트 최상단 경로를 현재 디렉토리로 설정
set PROJECT_ROOT=%~dp0
cd /d "%PROJECT_ROOT%"

:: 가상환경 활성화 (존재하는 경우)
if exist ".venv\Scripts\activate.bat" (
    echo [INFO] 가상환경 활성화 완료
    call ".venv\Scripts\activate.bat"
) else (
    echo [WARN] 가상환경을 찾을 수 없습니다. 글로벌 환경에서 실행합니다.
)

:: ---------------------------------------------------------
:: [2] 1단계: 가게 기본 정보 파이프라인 (meal_detail)
:: ---------------------------------------------------------
cd meal_detail

echo.
echo [STEP 1/5] 가게 목록/링크 수집 중... (01_collect_store_links.py)
python 01_collect_store_links.py --targets %TARGETS_FILE% %HEAD_MODE%
if %ERRORLEVEL% NEQ 0 goto :error

echo.
echo [STEP 2/5] 가게 상세 사이트 정보 수집 중... (02_collect_store_details.py)
python 02_collect_store_details.py %HEAD_MODE%
if %ERRORLEVEL% NEQ 0 goto :error

echo.
echo [STEP 3/5] 가게 정보 전처리 및 DB 업로드 중... (03_preprocess_and_upload.py)
python 03_preprocess_and_upload.py --host %DB_HOST% --port %DB_PORT% --dbname %DB_NAME% --user %DB_USER% --password %DB_PASS% --kakao-api-key "%KAKAO_API_KEY%" --truncate-first
if %ERRORLEVEL% NEQ 0 goto :error

cd ..

:: ---------------------------------------------------------
:: [3] 2단계: 가게 리뷰 파이프라인 (meal_review)
:: ---------------------------------------------------------
cd meal_review

echo.
echo [STEP 4/5] 가게 리뷰 및 이미지 수집 중... (02_collect_store_reviews.py)
python 02_collect_store_reviews.py %HEAD_MODE%
if %ERRORLEVEL% NEQ 0 goto :error

echo.
echo [STEP 5/5] 가게 리뷰 정보 DB 업로드 중... (03_preprocess_and_upload_reviews.py)
:: (참고) 리뷰쪽은 별도로 DB 포트를 입력받지 않게 설계된 경우를 대비함
python 03_preprocess_and_upload_reviews.py --host %DB_HOST% --dbname %DB_NAME% --user %DB_USER% --password %DB_PASS%
if %ERRORLEVEL% NEQ 0 goto :error

cd ..

echo.
echo ==========================================
echo [SUCCESS] 모든 크롤링 및 업로드 배치 작업이 완료되었습니다!
echo ==========================================
:: pause 명령어를 빼면 윈도우 스케줄러에서 자동 종료됩니다.
:: 확인이 필요하다면 아래 주석을 해제하세요.
:: pause
goto :eof

:error
echo.
echo ==========================================
echo [ERROR] 작업 중 오류가 발생하여 배치를 중단합니다. 
echo ==========================================
cd /d "%PROJECT_ROOT%"
pause
exit /b 1
