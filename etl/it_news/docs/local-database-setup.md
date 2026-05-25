# 로컬 PostgreSQL 기동 (it_news)

`etl/it_news` 파이프라인·DB 연결 테스트를 위해 개발용 DB를 띄우는 최소 절차이다.

---

## 1. 선행 조건

- Docker Desktop(Windows) 또는 Docker Engine
- 호스트 **5432** 포트 사용 가능 (다른 PostgreSQL과 충돌 시 중지)

---

## 2. DB 컨테이너 기동

Compose 파일 위치: 레포 `database/` (루트가 아님).

```powershell
cd C:\dev\project\SK-Connect\database
copy .env.example .env   # 최초 1회
docker compose up -d
```

| 항목 | 값 |
|------|-----|
| 컨테이너 | `sk_connect_db` |
| DB 이름 | `service` |
| 사용자 / 비밀번호 | `user` / `password` |
| 호스트 / 포트 | `localhost` / `5432` |

첫 기동 시 [database/init.sql](../../database/init.sql)로 `crawling` 등 스키마·`codeT` 시드가 적재된다.  
이미 볼륨이 있으면 `init.sql` 변경은 **자동 반영되지 않는다**. 스키마를 처음부터 다시 쓰려면 `docker compose down -v` 후 재기동(기존 데이터 삭제).

---

## 3. it_news 연결 설정

`etl/it_news/.env`에 아래를 맞춘다 (없으면 새로 작성).

```env
PGUSER=user
PGPASSWORD=password
PGHOST=localhost
PGPORT=5432
PGDATABASE=service
```

---

## 4. 동작 확인

컨테이너:

```powershell
docker ps
```

`sk_connect_db`가 보이면 된다.

it_news 루트에서 DB 연결·`crawling` 샘플 조회:

```powershell
cd C:\dev\project\SK-Connect\etl\it_news
python -m postgresql
```

테이블 목록만 보려면:

```powershell
docker exec -it sk_connect_db psql -U user -d service -c "\dt"
```

이후 단계·파이프라인 실행은 [design.md](./design.md)를 참고한다.

---

## 5. 중지

```powershell
cd C:\dev\project\SK-Connect\database
docker compose down
```

DB 데이터까지 초기화:

```powershell
docker compose down -v
```
