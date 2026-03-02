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

