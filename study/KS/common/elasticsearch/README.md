# Elasticsearch VectorDB 환경 구성

## 개요

Elasticsearch와 Kibana를 Docker Compose를 사용하여 로컬 개발 환경에 구성합니다.

## 포함된 서비스

### 1. Elasticsearch (포트: 9200, 9300)
- **버전**: 8.12.1
- **용도**: 벡터 검색 및 텍스트 검색 엔진
- **REST API**: http://localhost:9200
- **인증 정보**:
  - 사용자명: `elastic`
  - 비밀번호: `changeme123!`
- **주요 기능**:
  - 벡터 유사도 검색 (Dense Vector, HNSW)
  - 키워드 검색 (BM25)
  - 하이브리드 검색 (벡터 + 키워드)
  - 실시간 인덱싱 및 검색

### 2. Kibana (포트: 5601)
- **버전**: 8.12.1
- **용도**: Elasticsearch 관리 및 시각화 도구
- **Web UI**: http://localhost:5601
- **인증**: Elasticsearch 인증 정보 자동 사용
- **주요 기능**:
  - Dev Tools: Elasticsearch API 테스트
  - Discover: 데이터 탐색
  - Dashboard: 데이터 시각화
  - Index Management: 인덱스 관리

## 시작하기

### 1. Docker Compose 실행

```bash
cd elasticsearch
docker-compose up -d
```

### 2. 서비스 상태 확인

```bash
docker-compose ps
```

### 3. Elasticsearch 클러스터 상태 확인

```bash
curl -u elastic:changeme123! http://localhost:9200/_cluster/health
```

### 4. Kibana Web UI 접속

브라우저에서 http://localhost:5601 접속

## 주요 엔드포인트

### Elasticsearch REST API (인증 필요)

모든 API 호출 시 `-u elastic:changeme123!` 옵션을 사용하여 인증합니다.

- **클러스터 상태**: `GET http://localhost:9200/_cluster/health`
  ```bash
  curl -u elastic:changeme123! http://localhost:9200/_cluster/health
  ```

- **인덱스 목록**: `GET http://localhost:9200/_cat/indices?v`
  ```bash
  curl -u elastic:changeme123! http://localhost:9200/_cat/indices?v
  ```

- **노드 정보**: `GET http://localhost:9200/_cat/nodes?v`
  ```bash
  curl -u elastic:changeme123! http://localhost:9200/_cat/nodes?v
  ```

- **인덱스 통계**: `GET http://localhost:9200/<index_name>/_stats`
- **인덱스 매핑**: `GET http://localhost:9200/<index_name>/_mapping`

### 검색 API

- **벡터 검색**: `POST http://localhost:9200/<index_name>/_search`
- **키워드 검색**: `POST http://localhost:9200/<index_name>/_search`

## 데이터 영속성

- Elasticsearch 데이터는 `./database` 디렉토리에 저장됩니다.
- 컨테이너를 삭제해도 데이터는 유지됩니다.

## 중지 및 재시작

### 서비스 중지
```bash
docker-compose stop
```

### 서비스 재시작
```bash
docker-compose start
```

### 서비스 종료 (컨테이너 삭제)
```bash
docker-compose down
```

### 서비스 종료 및 볼륨 삭제
```bash
docker-compose down -v
```

## 로그 확인

```bash
# 전체 로그
docker-compose logs

# Elasticsearch 로그만
docker-compose logs elasticsearch

# Kibana 로그만
docker-compose logs kibana

# 실시간 로그 (follow)
docker-compose logs -f
```

## 환경 설정

### 메모리 설정

기본값은 1GB로 설정되어 있습니다. 더 많은 메모리가 필요한 경우 `docker-compose.yml`에서 수정:

```yaml
environment:
  - "ES_JAVA_OPTS=-Xms2g -Xmx2g"  # 2GB로 증가
```

**권장사항**:
- 개발 환경: 1-2GB
- 운영 환경: 시스템 메모리의 50% (최대 31GB)

## 보안 설정

현재 설정은 개발 환경용으로 **기본 인증(Basic Authentication)이 활성화**되어 있습니다.

- ✅ **X-Pack Security**: 활성화
- ✅ **기본 인증**: 활성화
- ⚠️ **SSL/TLS**: 비활성화 (개발 환경용)

### 운영 환경 권장사항

1. **강력한 비밀번호 사용**
   - 현재 비밀번호(`changeme123!`)는 예시용입니다
   - 운영 환경에서는 강력한 비밀번호로 변경하세요

2. **SSL/TLS 활성화** (HTTPS)
   ```yaml
   environment:
     - xpack.security.http.ssl.enabled=true
     - xpack.security.transport.ssl.enabled=true
   ```

3. **사용자 역할 관리**
   - 최소 권한 원칙 적용
   - 역할 기반 접근 제어(RBAC) 설정

## 문제 해결

### 1. Elasticsearch가 시작되지 않는 경우

**메모리 부족**:
- Docker Desktop의 메모리 할당 확인 (최소 4GB 권장)
- `ES_JAVA_OPTS` 설정 확인

**포트 충돌**:
```bash
# 포트 사용 확인
netstat -an | findstr :9200
```

### 2. 헬스체크 실패

```bash
# Elasticsearch 로그 확인
docker-compose logs elasticsearch

# 컨테이너 재시작
docker-compose restart elasticsearch
```

### 3. Kibana가 Elasticsearch에 연결되지 않는 경우

```bash
# Elasticsearch가 먼저 실행 중인지 확인
curl -u elastic:changeme123! http://localhost:9200

# Kibana 재시작
docker-compose restart kibana
```

### 4. 인증 오류 (401 Unauthorized)

보안이 활성화되어 있으므로 모든 API 호출 시 인증이 필요합니다:

```bash
# 잘못된 예시 (인증 없음)
curl http://localhost:9200/_cluster/health
# 오류: {"error":{"root_cause":[{"type":"security_exception","reason":"missing authentication credentials"}]}}

# 올바른 예시 (인증 포함)
curl -u elastic:changeme123! http://localhost:9200/_cluster/health
```

## Python 클라이언트 설정

### 필요한 패키지

```bash
pip install langchain-elasticsearch elasticsearch
```

### 연결 예제

#### 방법 1: elasticsearch 패키지 직접 사용 (권장)

```python
from elasticsearch import Elasticsearch

# 인증 정보 포함하여 연결
es_client = Elasticsearch(
    ["http://localhost:9200"],
    basic_auth=("elastic", "changeme123!"),  # 인증 정보 필수
    verify_certs=False
)

# 연결 테스트
if es_client.ping():
    print("연결 성공!")
    info = es_client.info()
    print(f"버전: {info['version']['number']}")
```

#### 방법 2: LangChain ElasticsearchStore 사용

```python
from langchain_elasticsearch import ElasticsearchStore
from langchain_ollama import OllamaEmbeddings

embeddings = OllamaEmbeddings(model="qwen3-embedding:0.6b")

# es_user와 es_password 파라미터로 인증 정보 전달
vectorstore = ElasticsearchStore(
    es_url="http://localhost:9200",
    index_name="my_index",
    embedding=embeddings,
    es_user="elastic",
    es_password="changeme123!"
)
```

## 참고 자료

- [Elasticsearch 공식 문서](https://www.elastic.co/guide/en/elasticsearch/reference/current/index.html)
- [Kibana 사용 가이드](https://www.elastic.co/guide/en/kibana/current/index.html)
- [Docker Compose 문서](https://docs.docker.com/compose/)
- [LangChain Elasticsearch 통합](https://docs.langchain.com/oss/python/integrations/vectorstores/elasticsearch)

## 라이선스

- Elasticsearch: Elastic License 2.0 & SSPL
- 자세한 내용: https://www.elastic.co/pricing/faq/licensing

