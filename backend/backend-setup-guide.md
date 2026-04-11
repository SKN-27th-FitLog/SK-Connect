# Backend 프로젝트 환경 설정 가이드

이 문서는 **Python 3.12 + Django + Docker + PostgreSQL** 기반  
백엔드 개발 환경을 팀원 모두가 동일하게 구축하기 위한 표준 가이드입니다.

---

# 📁 프로젝트 폴더 구조

```
<레포 루트>/
<<<<<<< HEAD
├── backend/                    # Django 백엔드
│   ├── .venv/                  # Python 가상환경(로컬)
│   ├── manage.py               # Django 실행 진입점
│   ├── requirements.txt
│   ├── .env                    # 로컬 환경변수(개인)
│   ├── config/                 # 프로젝트 설정
│   │   ├── __init__.py
│   │   ├── settings.py         # DB, 앱, 환경설정
│   │   ├── urls.py             # API 라우팅
│   │   ├── wsgi.py
│   │   └── asgi.py
│   ├── common/                 # 공통 모델/유틸
│   ├── users/                  # 사용자
│   ├── places/                 # 지도/가게/메뉴
│   ├── crawling/               # 크롤링
│   └── community/              # 게시글/댓글/좋아요
├── database/                   # PostgreSQL (Docker)
│   ├── docker-compose.yml      # DB 컨테이너 실행은 여기서
│   ├── init.sql                # 테이블 생성/초기 데이터 로드
│   └── data/                   # init.sql에서 참조하는 CSV 등
└── doc/                        # ERD/문서
=======
├── Dockerfile
├── backend/
│   ├── manage.py
│   ├── requirements.txt
│   ├── .env.example
│   ├── .env
│   ├── config/             # Django 프로젝트 설정 (settings, urls, wsgi, asgi)
│   ├── common/             # 공통 모델/유틸
│   ├── users/              # 사용자 도메인
│   ├── places/             # 장소 도메인
│   ├── community/          # 커뮤니티 도메인
│   └── crawling/           # 크롤링 도메인
└── database/
    ├── docker-compose.yml  # PostgreSQL 컨테이너 실행
    ├── .env.example
    ├── .env
    ├── init.sql            # DB 초기 스키마/데이터
    └── data/               # 초기 적재용 데이터 파일(선택)
>>>>>>> origin/dev
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


---

```


#  최초 실행 Quick Start (요약)

처음 세팅 시 아래 순서만 실행하면 됩니다.

```bash
git clone <repository-url>

uv venv .venv --python 3.12
.\.venv\Scripts\activate

uv pip install -r requirements.txt

copy .env.example .env



```

