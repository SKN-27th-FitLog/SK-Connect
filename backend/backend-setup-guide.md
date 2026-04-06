# 🚀 Backend 프로젝트 환경 설정 가이드

이 문서는 **Python 3.12 + Django + Docker + PostgreSQL** 기반  
백엔드 개발 환경을 팀원 모두가 동일하게 구축하기 위한 표준 가이드입니다.

---

# 📁 프로젝트 폴더 구조

```
<레포 루트>/
├── docker-compose.yml  # Docker (DB + web) — 루트에서 실행
├── Dockerfile          # web 이미지 빌드 (context = 레포 루트)
├── postgres-init/      # PostgreSQL 초기화 스크립트 (선택)
└── backend/
    ├── .venv/          # Python 가상환경
    ├── manage.py       # Django 실행 진입점 (서버, DB 관리)
    ├── config/         # 프로젝트 설정
    │   ├── __init__.py
    │   ├── settings.py # DB, 앱, 환경설정
    │   ├── urls.py     # API 라우팅
    │   ├── wsgi.py
    │   └── asgi.py
    ├── requirements.txt
    └── .env
```

---

## ✅ 1. 프로젝트 다운로드

```bash
git clone <repository-url>
cd <레포-폴더명>
```

---

## ✅ 2. 가상환경 생성

패키지 충돌 방지를 위해 `backend` 내부에 생성합니다.

```bash
cd backend
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
python -c "import secrets; print(secrets.token_urlsafe(50))"
```

출력된 값을 `.env`에 추가:

```
SECRET_KEY=생성된값
```

---

## ✅ 7. Database 환경 변수 설정

`.env` 값은 반드시 `docker-compose.yml`과 동일해야 합니다.

```

### ⚠️ 주의사항

- `.env.example` 에 SECRET_KEY 작성 ❌  
- 실제 키는 `.env`에만 작성  
- DB 정보 불일치 시 접속 실패  

---

## ✅ 8. Docker 실행

**레포지토리 루트**(`docker-compose.yml`이 있는 디렉터리)에서 실행합니다.

```bash
cd ..   # 이미 backend 안에 있다면 루트로
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

~~Django 명령어는 **반드시 web 컨테이너 내부**에서 실행합니다.~~


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


# 🚀 최초 실행 Quick Start (요약)

처음 세팅 시 아래 순서만 실행하면 됩니다.

```bash
git clone <repository-url>
cd <레포-폴더명>

cd backend
uv venv .venv --python 3.12
.\.venv\Scripts\activate

uv pip install -r requirements.txt

copy .env.example .env

cd ..
docker compose up -d --build

cd backend
python manage.py migrate

```

