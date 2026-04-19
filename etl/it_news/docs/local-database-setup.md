# 로컬 PostgreSQL 기동 가이드 (it_news / 공용)

이 문서는 레포의 **`database/docker-compose.yml`** 로 개발용 DB를 띄울 때의 절차입니다.  
백엔드 팀 가이드(`backend/backend-setup-guide.md`)의 Docker 예시는 레포 구조와 다를 수 있으므로, **기동 경로는 이 문서를 기준**으로 맞추면 됩니다.

---

## 1. 선행 조건

- Docker Desktop(Windows) 또는 Docker Engine 설치
- 호스트의 **5432** 포트가 비어 있을 것 (다른 PostgreSQL이 쓰 중이면 충돌)

---

## 2. Compose 실행 위치

`docker-compose.yml`은 **레포 루트가 아니라 `database/` 폴더**에만 있습니다.

PowerShell 예시 (레포 루트 `SK-Connect` 기준):

```powershell
cd C:\dev\project\SK-Connect\database
docker compose up -d
```

백엔드 폴더에서 상대 경로로 가려면:

```powershell
cd ..\database
docker compose up -d
```

---

## 3. 컨테이너·DB 정보 (환경 변수와 맞추기)

아래 값은 [database/docker-compose.yml](../../database/docker-compose.yml)과 [backend/.env.example](../../backend/.env.example)가 서로 맞도록 잡혀 있습니다.

| 항목 | 값 |
|------|-----|
| 컨테이너 이름 | `sk_connect_db` |
| PostgreSQL 이미지 | `postgres:16` |
| DB 이름 (`POSTGRES_DB` / `SERVICE_DB_NAME`) | `service` |
| 사용자 (`POSTGRES_USER` / `DB_USER`) | `user` |
| 비밀번호 (`POSTGRES_PASSWORD` / `DB_PASSWORD`) | `password` |
| 호스트(로컬에서 접속) | `localhost` |
| 포트 | `5432` |

백엔드에서 쓰려면 `backend`에 `.env`를 두고, `backend/.env.example`을 복사한 뒤 `SECRET_KEY` 등만 채우면 됩니다.

`etl/it_news` 파이프라인은 이제 루트 공용 환경변수만 보지 않고, 각 스테이지 폴더의 로컬 설정 파일을 직접 읽습니다.

- `etl/it_news/crawling/.env`
- `etl/it_news/cleaning/.env`
- `etl/it_news/save/.env`

또한 운영용 고정값은 아래 `config.json`에서 읽습니다.

- `etl/it_news/crawling/config.json`
- `etl/it_news/cleaning/config.json`
- `etl/it_news/save/config.json`

---

## 4. 초기화 스크립트·데이터 볼륨

- 첫 기동 시 [database/init.sql](../../database/init.sql)이 실행되고, `codeT` 등 스키마가 만들어진 뒤 [database/data/codeT.csv](../../database/data/codeT.csv)가 `COPY` 됩니다.
- 이 초기화는 **PostgreSQL 데이터 디렉터리(볼륨 `postgres_data`)가 비어 있을 때 한 번만** 실행됩니다.
- 이미 컨테이너를 띄운 적이 있어 볼륨이 남아 있으면, `init.sql`을 수정해도 **자동으로 다시 적용되지 않습니다**. 스키마를 처음부터 다시 넣으려면 볼륨 삭제 후 재기동 등이 필요하며, **기존 DB 데이터는 삭제**될 수 있으니 주의하세요.

---

## 5. (선택) 보조 DB `data`

`backend/.env.example`에는 `DATA_DB_NAME=data`가 있습니다.  
Compose의 `POSTGRES_DB`는 `service`만 만들기 때문에, **기본 설정만으로는 `data` 데이터베이스가 없을 수 있습니다.**

Django 등에서 `secondary` DB를 쓰기 전에 필요하면, 예를 들어 다음처럼 한 번 만들 수 있습니다.

```powershell
docker exec -it sk_connect_db psql -U user -d service -c "CREATE DATABASE data;"
```

팀에서 `database` 초기화 스크립트로 자동화할 수도 있습니다.

---

## 6. 백엔드 연동 (참고)

DB만 it_news·크롤링 등에 쓰고 Django는 아직 안 쓸 경우 이 단계는 생략해도 됩니다.

1. `backend`에서 `.env.example` → `.env` 복사 후 `SECRET_KEY` 설정  
2. DB 컨테이너가 떠 있는 상태에서:

```powershell
cd C:\dev\project\SK-Connect\backend
python manage.py migrate
```

마이그레이션 파일 유무·`init.sql`과의 역할 분담은 팀 정책에 따릅니다.

---

## 7. 동작 확인 (직접 실행할 때)

컨테이너 상태:

```powershell
docker ps
```

`sk_connect_db`가 보이면 됩니다.

`comments` 저장까지 검증하려면 `users` 테이블에 참조 가능한 사용자 행이 하나 이상 있어야 하며, 실행 시 `save/.env`의 `IT_NEWS_COMMENT_USER_ID` 또는 `run_comment_save.py --user-id`로 그 `user_id`를 넘겨야 합니다.

테이블 존재 여부 예시:

```powershell
docker exec -it sk_connect_db psql -U user -d service -c "\dt"
```

---

## 8. DBeaver로 PostgreSQL 접속

**전제:** §7까지처럼 컨테이너 `sk_connect_db`가 떠 있고, 호스트에서 `localhost:5432`로 접근 가능할 것.

1. [DBeaver Community](https://dbeaver.io/download/) 등으로 DBeaver를 설치합니다.
2. **Database** → **New Database Connection** → **PostgreSQL**을 선택합니다.
3. **Main**(또는 Connection) 탭에서 아래와 같이 입력합니다(§3 표와 동일).

   | 항목 | 값 |
   |------|-----|
   | Host | `localhost` |
   | Port | `5432` |
   | Database | `service` |
   | Username | `user` |
   | Password | `password` |

   비밀번호 저장 여부는 로컬 정책에 맞게 선택하면 됩니다.
4. **SSL** 탭: 로컬 Docker 개발이면 SSL을 끕니다(예: SSL 사용 안 함 / SSL mode `disable`).
5. **Test Connection**을 누릅니다. 최초에는 PostgreSQL JDBC 드라이버 다운로드 안내가 나올 수 있으므로, 다운로드·허용 후 다시 테스트합니다.
6. **Finish**로 저장한 뒤, 왼쪽 네비게이터에서 `service` → **Schemas** → **public** 아래 테이블을 확인하면 §7의 `\dt`와 같은 점검을 GUI로 할 수 있습니다.

---

## 9. 중지·삭제

중지:

```powershell
cd C:\dev\project\SK-Connect\database
docker compose down
```

볼륨까지 지우고 완전히 초기화하려면(데이터 삭제):

```powershell
docker compose down -v
```
