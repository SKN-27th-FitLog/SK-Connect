

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

## ✅ 5. `.env` 파일 생성 (database폴더)

### Windows
```bash
copy .env.example .env
```

### Mac / Linux
```bash
cp .env.example .env
```

---


## ✅ 7. Database 환경 변수 설정

`.env` 값은 반드시 `docker-compose.yml`과 동일해야 합니다.

```


## ✅ 8. Docker 실행

**database폴더**(`docker-compose.yml`이 있는 디렉터리)에서 실행합니다.

```bash
cd ..   # 이미 backend 안에 있다면 루트로
docker compose up -d
```

실행 확인:

```bash
docker ps
```