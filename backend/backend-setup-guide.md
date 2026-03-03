# 🚀 Backend 프로젝트 환경 설정 가이드

이 문서는 Python 3.12를 기반으로 백엔드 개발 환경을 설정하고 가상환경(`venv`)을 관리하는 표준 방법을 안내합니다.

---

## 1. Python 3.12 
프로젝트의 안정성과 속도를 위해 **Python 3.12** 사용을 권장합니다.



---

## 2. 가상환경(venv) 설정

백엔드 패키지 간의 충돌을 방지하기 위해 `backend` 폴더 내부에 독립적인 가상환경을 생성합니다.

### 📂 폴더 이동
```bash
cd backend

# 'venv'라는 이름의 폴더로 가상환경 생성
uv venv .venv --python 3.12

```
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
```

## 4..env.exmaple 복사하여 .env파일 만들기

=========================================================
# 🚀 Backend Setup Guide

본 문서는 프로젝트 백엔드 개발 환경을 처음 세팅하는 방법을 설명합니다.

---

## ✅ 1. 프로젝트 Clone

```bash
git clone <repository-url>
cd backend
```

---

## ✅ 2. Python 가상환경 생성

### Windows

```bash
python -m venv venv
venv\Scripts\activate
```

### Mac / Linux

```bash
python3 -m venv venv
source venv/bin/activate
```

---

## ✅ 3. 패키지 설치

```bash
pip install -r requirements.txt
```

---

## ✅ 4. 환경변수(.env) 설정

`backend` 폴더에 `.env` 파일 생성

```env
SECRET_KEY=django-secret-key
DEBUG=True

DB_NAME=postgres
DB_USER=community
DB_PASSWORD=password123
DB_HOST=db
DB_PORT=5432
```

---

## ✅ 5. Docker 실행 (PostgreSQL)

```bash
docker compose up -d
```

확인:

```bash
docker ps
```

PostgreSQL 컨테이너가 실행 중이면 정상입니다.

---

## ✅ 6. Database Migration

테이블 생성 단계입니다.

```bash
python manage.py migrate
```

---

## ✅ 7. 관리자 계정 생성 (선택)

```bash
python manage.py createsuperuser
```

---

## ✅ 8. 더미 데이터 생성 (권장)

개발용 테스트 데이터를 자동 생성합니다.

```bash
python manage.py seed
```

---

## ✅ 9. 서버 실행

```bash
python manage.py runserver
```

접속:

```
http://127.0.0.1:8000/
```

Admin 페이지:

```
http://127.0.0.1:8000/admin
```

---

## ✅ 10. (선택) Fixture 데이터 로드

공통 테스트 데이터가 필요한 경우:

```bash
python manage.py loaddata fixtures/common.json
python manage.py loaddata fixtures/map.json
python manage.py loaddata fixtures/posts.json
python manage.py loaddata fixtures/interactions.json
```

---

# 📦 전체 실행 순서 (Quick Start)

```bash
git pull origin dev

python -m venv venv
venv\Scripts\activate

pip install -r requirements.txt

docker compose up -d

python manage.py migrate
python manage.py seed

python manage.py runserver
```

---

# ⚠️ 주의사항

* Docker 실행 없이 Django 서버 실행 시 DB 연결 오류 발생
* Migration 파일은 반드시 Git에 포함되어야 함
* DB 데이터는 Git으로 공유되지 않음 (fixture 또는 seed 사용)

---

# ✅ 개발 준비 완료

위 과정을 완료하면 동일한 개발 환경에서 백엔드 개발을 시작할 수 있습니다.
