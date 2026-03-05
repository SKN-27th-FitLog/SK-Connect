# 🚀 Backend 프로젝트 환경 설정 가이드

이 문서는 **Python 3.12 + Django + Docker + PostgreSQL** 기반  
백엔드 개발 환경을 팀원 모두가 동일하게 구축하기 위한 표준 가이드입니다.

---

# 📁 프로젝트 폴더 구조

```
backend/
├── .venv/              # Python 가상환경
├── manage.py           # Django 실행 진입점 (서버, DB 관리)
├── config/             # 프로젝트 설정
│   ├── __init__.py
│   ├── settings.py     # DB, 앱, 환경설정
│   ├── urls.py         # API 라우팅
│   ├── wsgi.py
│   └── asgi.py
├── docker-compose.yml
├── requirements.txt
└── .env
```

---

## ✅ 1. 프로젝트 다운로드

```bash
git clone <repository-url>
cd backend
```

---

## ✅ 2. 가상환경 생성

패키지 충돌 방지를 위해 backend 내부에 생성합니다.

```bash
uv venv .venv --python 3.12
```

---

## ✅ 3. 가상환경 활성화

### Windows (PowerShell)

```bash
.\.venv\Scripts\activate
```

### Mac / Linux

```bash
source .venv/bin/activate
```

정상 활성화 시:

```
(.venv)
```

표시가 앞에 나타납니다.

---

## ✅ 4. Python 패키지 설치

```bash
uv pip install -r requirements.txt
```

---

## ✅ 5. `.env` 파일 생성

### Windows
```bash
copy .env.example .env
```

### Mac / Linux
```bash
cp .env.example .env
```

---

## ✅ 6. SECRET_KEY 생성

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

출력된 값을 `.env`에 추가:

```
SECRET_KEY=생성된값
```

---

## ✅ 7. Database 환경 변수 설정

`.env` 값은 반드시 `docker-compose.yml`과 동일해야 합니다.

```
POSTGRES_DB=community
POSTGRES_USER=community
POSTGRES_PASSWORD=community

DB_HOST=db
DB_PORT=5432
```

### ⚠️ 주의사항

- `.env.example` 에 SECRET_KEY 작성 ❌  
- 실제 키는 `.env`에만 작성  
- DB 정보 불일치 시 접속 실패  

---

## ✅ 8. Docker 실행

backend 폴더에서 실행:

```bash
docker compose up -d --build
```

실행 확인:

```bash
docker ps
```

다음 컨테이너가 보여야 정상:

```
web
db
```

---

## ✅ 9. Web 컨테이너 접속

Django 명령어는 **반드시 web 컨테이너 내부**에서 실행합니다.

```bash
docker compose exec web bash
```

bash 오류 발생 시:

```bash
docker compose exec web sh
```

---

## ✅ 10. Database Migration ⭐ (매우 중요)

```bash
python manage.py migrate
```

정상 출력:

```
Applying ...
OK
```

👉 이 과정에서 **DB 테이블이 생성됩니다**

---

## ✅ 11. Seed 데이터 반영 (팀 공통 데이터)

초기 데이터 생성:

```bash
python manage.py seed
```

👉 게시글 / 유저 / 테스트 데이터가 DB에 생성됩니다.

---

## ✅ 12. 서버 실행 확인

브라우저 접속:

```
http://localhost:8000
```

페이지가 열리면 정상입니다.

---

## ✅ 13. DBeaver DB 확인

PostgreSQL 연결 생성

| 항목 | 값 |
|---|---|
| Host | localhost |
| Port | 5432 |
| Database | community |
| Username | community |
| Password | community |

연결 후:

```
Schemas
 └ public
    └ Tables
```

👉 우클릭 → **Refresh**

---

## ✅ 14. Pull 이후 팀원이 반드시 해야 할 작업

새 migration 또는 seed 변경 시:

```bash
docker compose exec web python manage.py migrate
docker compose exec web python manage.py seed
```

---

## ✅ 15. 컨테이너 종료

### 일반 종료
```bash
docker compose down
```

### DB 포함 완전 초기화 ⚠️
```bash
docker compose down -v
```

⚠️ 모든 DB 데이터 삭제됨

---

# 🚀 최초 실행 Quick Start (요약)

처음 세팅 시 아래 순서만 실행하면 됩니다.

```bash
git clone <repository-url>
cd backend

uv venv .venv --python 3.12
.\.venv\Scripts\activate

uv pip install -r requirements.txt

copy .env.example .env

docker compose up -d --build

docker compose exec web bash
python manage.py migrate
python manage.py seed
```

---

## 🌐 웹 서버는 테스트용
---