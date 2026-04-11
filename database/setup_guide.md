

## ✅ 5. `.env` 파일 생성


### Windows
```bash
copy .env.example .env
```

### Mac / Linux
```bash
cp .env.example .env
```

===================================

## ✅ 7. Database 환경 변수 설정

`.env` 값은 반드시 `docker-compose.yml`과 동일해야 합니다.

### ⚠️ 주의사항

- 실제 키는 `.env`에만 작성  
- DB 정보 불일치 시 접속 실패  

---


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