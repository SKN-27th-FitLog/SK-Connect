# 🚀 Backend 프로젝트 환경 설정 가이드

이 문서는 Python 3.12를 기반으로 백엔드 개발 환경을 설정하고 가상환경(`venv`)을 관리하는 표준 방법을 안내합니다.

## 3. 폴더 구조

```
backend/
├── .venv/            (아까 만든 가상환경)
├── manage.py         <-- 앞으로 가장 많이 쓸 실행 파일 (서버 실행, DB 마이그레이션 등)
├── config/           <-- 프로젝트의 '뇌' 역할을 하는 설정 폴더
│   ├── __init__.py
│   ├── settings.py   <-- DB 설정, 라이브러리 등록 등을 여기서 함
│   ├── urls.py       <-- API 주소를 정의하는 곳
│   └── wsgi.py / asgi.py
└── requirements.txt
`✅ 2. 프로젝트 다운로드
git clone <repository-url>
cd backend
✅ 3. 가상환경(venv) 생성

패키지 충돌 방지를 위해 backend 내부에 가상환경을 생성합니다.

uv venv .venv --python 3.12
✅ 4. 가상환경 활성화
✅ Windows (PowerShell)
.\.venv\Scripts\activate
✅ Mac / Linux
source .venv/bin/activate

정상 활성화 시:

(.venv)

가 앞에 표시됩니다.

✅ 5. Python 패키지 설치
uv pip install -r requirements.txt
✅ 6. .env 파일 생성

.env.example을 복사하여 .env 생성

Windows
copy .env.example .env
Mac / Linux
cp .env.example .env
✅ 7. SECRET_KEY 생성

아래 명령어 실행:

python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"

출력된 값을 .env에 추가:

SECRET_KEY=여기에_붙여넣기
✅ 8. Database 환경 변수 설정

.env 파일 내용은 반드시 docker-compose.yml과 동일해야 합니다.

POSTGRES_DB=community
POSTGRES_USER=community
POSTGRES_PASSWORD=community

DB_HOST=db
DB_PORT=5432

✅ 주의사항

.env.example에는 SECRET_KEY 작성 ❌

실제 SECRET_KEY는 .env에만 작성

DB 정보가 다르면 접속 실패

✅ 9. Docker 실행

backend 폴더에서 실행:

docker compose up -d --build
실행 확인
docker ps

다음 컨테이너가 보여야 정상:

web
db
✅ 10. Web 컨테이너 접속

Django 명령어는 반드시 web 컨테이너 내부에서 실행합니다.

docker compose exec web bash

만약 bash 오류 발생 시:

docker compose exec web sh
✅ 11. Database Migration ⭐ (매우 중요)

컨테이너 내부에서 실행:

python manage.py migrate

정상 출력:

Applying ...
OK

✅ 이 과정에서 DB 테이블이 생성됩니다.

✅ 12. 서버 실행 확인

브라우저 접속:

http://localhost:8000

페이지가 열리면 정상입니다.

✅ 13. DBeaver DB 확인

PostgreSQL 연결 생성

항목	값
Host	localhost
Port	5432
Database	community
Username	community
Password	community

연결 후:

Schemas
 └ public
    └ Tables

👉 우클릭 Refresh

✅ 14. Pull 이후 해야 하는 작업 (팀원 필수)

새 migration이 추가되었을 경우:

docker compose exec web python manage.py migrate
✅ 15. 컨테이너 종료
일반 종료
docker compose down
DB 포함 완전 초기화
docker compose down -v

⚠️ DB 데이터 모두 삭제됨

✅ 🚀 최초 실행 Quick Start (요약)

처음 세팅 시 아래만 순서대로 실행하면 됩니다.

git clone <repository-url>
cd backend

uv venv .venv --python 3.12
.\.venv\Scripts\activate

uv pip install -r requirements.txt

copy .env.example .env

docker compose up -d --build
docker compose exec web bash
python manage.py migrate