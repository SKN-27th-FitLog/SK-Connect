# Neo4j 개선 비교 및 정리 가이드

## 1. 문서 목적

- 이 문서는 외부 참고 구현인 `common/n4j`와 현재 구현인 `Neo4j`를 비교한 뒤, 내 코드에 적용할 개선 사항을 정리하기 위한 작업 기준서다.
- 실제 리팩터링 전에 구조를 바로 확정할 수 있는 항목과, 판단이 더 필요한 항목을 분리해서 관리한다.
- 이후 Neo4j 관련 작업은 이 문서를 계속 수정하면서 진행한다.

## 2. 비교 범위

- 외부 참고 구현
  - `common/n4j/n4j_connection.py`
  - `common/n4j/n4j_query_templates.py`
  - `common/db/connection.py`
- 현재 구현
  - `Neo4j/connenct_neo4j.py`
  - `Neo4j/qurry_neo4j.py`
  - `Neo4j/import_neo4j.py`
  - `Neo4j/clear_database_neo4j.py`
  - `Neo4j/data_cleaning.py`

## 3. 현재 구조 요약

### 3-1. 외부 참고 구현의 특징

- `Neo4j_Connection` 클래스가 드라이버와 임베딩 모델을 함께 보유한다.
- 실행 책임이 클래스 메서드에 모여 있다.
  - `execute_query()`
  - `execute_query_templates()`
- 쿼리 포맷은 `CypherQueryTemplates` Enum에 모아두고, `build()`로 최종 Cypher 문자열을 생성한다.
- 연결 객체는 `Singleton` 메타클래스를 사용해서 재사용한다.

### 3-2. 현재 구현의 특징

- `get_neo4j_driver()` 함수가 드라이버와 GDS 객체를 생성해서 반환한다.
- 공통 실행은 `run_query()` 함수에 있고, 테이블별 적재 로직은 `import_equipment()` 같은 함수로 분리되어 있다.
- 실제 적재 흐름은 `import_neo4j.py`에서 드라이버를 열고, `iterrows()`를 돌면서 `session.execute_write()`를 반복 호출한다.
- 파일 책임이 나뉘어 있기는 하지만, 연결 관리와 도메인 로직의 경계가 아직 명확하게 고정되지는 않았다.

## 4. 핵심 차이 정리

### 4-1. 연결 관리

- 외부 참고 구현은 연결을 클래스로 감싸고, 클래스 인스턴스를 재사용하는 방식이다.
- 현재 구현은 함수 호출 시마다 드라이버/GDS를 반환하는 구조다.
- 개선 포인트:
  - 연결 상태, 세션 생성, 공통 실행, 종료 처리는 클래스 하나로 모으는 편이 이후 재사용에 유리하다.
  - 다만 외부 구현의 `Singleton` 메타클래스를 그대로 복제하기보다, 먼저 명시적인 `Neo4jClient` 클래스로 정리한 뒤 싱글톤 적용 여부를 나중에 결정하는 편이 안전하다.

### 4-2. 기능 배치

- 외부 참고 구현은 기능이 연결 객체의 메서드에 붙어 있다.
- 현재 구현은 공통 실행과 도메인별 적재가 함수 중심이다.
- 개선 포인트:
  - 공통 기능은 메서드로 이동하는 것이 적합하다.
  - 도메인별 적재와 조회까지 전부 클래스 메서드로 몰아넣을지는 보류가 필요하다.

### 4-3. 확장 전략

- 외부 참고 구현은 동일한 포맷의 조회 문제를 템플릿으로 다루는 데 적합하다.
- 현재 구현은 `Equipment` 외에 다른 테이블도 존재할 수 있어, 테이블마다 컬럼 매핑과 Cypher 구조가 달라질 가능성이 크다.
- 개선 포인트:
  - 공통 실행 인터페이스는 통일하되, 도메인별 쿼리 정의는 분리 가능한 구조로 유지하는 것이 더 적합하다.
  - 조회 템플릿과 적재 템플릿은 같은 방식으로 묶기 어려울 수 있으므로 분리해서 판단해야 한다.

## 5. 바로 반영할 개선 방향

### 5-1. 연결 객체는 클래스 기반으로 정리

- `get_neo4j_driver()` 중심 구조 대신 `Neo4jClient` 같은 클래스를 둔다.
- 이 클래스는 다음 책임을 가진다.
  - 환경변수 또는 설정값으로 드라이버 생성
  - 공통 쿼리 실행
  - write/read 트랜잭션 래핑
  - 드라이버 종료
  - 필요 시 GDS 객체 접근 제공

### 5-2. 공통 기능과 도메인 기능을 분리

- 클래스에 두는 책임
  - 드라이버 생성
  - 세션 생성
  - 공통 `run_query`
  - `execute_read`, `execute_write` 같은 공통 래퍼
  - 공통 예외 처리 및 로깅
- 별도 함수 또는 모듈에 두는 책임
  - `Equipment` 전용 Cypher
  - 테이블별 컬럼 매핑
  - CSV 전처리 규칙
  - 적재 순서 제어

### 5-3. 추천 기본안

- 1차 방향은 다음과 같이 잡는다.
  - 연결과 공통 실행은 클래스화
  - 도메인별 적재/조회 로직은 분리 유지
  - 필요 시 도메인 모듈이 `Neo4jClient` 객체를 받아 실행
- 이 방식이면 외부 참고 구현의 장점인 호출 일관성을 가져오면서도, 여러 테이블을 처리할 때 클래스가 비대해지는 문제를 줄일 수 있다.

## 6. 판단이 필요한 항목

이 섹션은 확정 전에는 짧게 유지하고, 방향이 정해지면 세부 설계와 예시를 추가한다.

### 6-1. 싱글톤 적용 여부

- 판단 포인트
  - 애플리케이션 실행 중 연결 객체를 하나만 유지해야 하는가
  - 테스트 시 새 연결 객체 생성이 필요한가
  - Streamlit 또는 배치 실행에서 재사용 정책이 같은가
- 현재 권장
  - 먼저 일반 클래스 형태로 정리
  - 실제 사용 패턴이 확인되면 싱글톤 또는 캐시 적용 여부를 결정

### 6-2. 도메인 로직을 메서드로 둘지 함수로 둘지

- 클래스 메서드가 적합한 경우
  - 연결 상태를 전제로 동작하는 공통 기능
  - 여러 도메인에서 공통으로 쓰는 실행 래퍼
  - 세션/트랜잭션 제어
- 별도 함수가 적합한 경우
  - 특정 테이블 전용 Cypher
  - 컬럼명과 노드/관계 매핑
  - 전처리 규칙
  - 적재 파이프라인의 단계별 조합
- 현재 권장
  - `import_equipment(client, row)` 같은 함수 주입 방식부터 시작
  - 여러 테이블에서 완전히 동일한 패턴이 반복될 때만 메서드 승격 검토

### 6-3. 템플릿 방식 적용 범위

- 조회 쿼리는 외부 참고 구현처럼 템플릿화가 비교적 잘 맞는다.
- 적재 쿼리는 테이블별 차이가 커질 수 있어서, 무리하게 Enum 템플릿 하나로 통합하면 오히려 복잡해질 수 있다.
- 현재 권장
  - 조회 계열부터 템플릿화 검토
  - 적재 계열은 도메인별 모듈 분리 후 반복 패턴이 보일 때 공통화

## 7. 판단 체크리스트

새 기능을 추가할 때 아래 질문으로 메서드화 여부를 판단한다.

- 이 기능이 드라이버/세션 상태를 직접 다루는가
- 여러 테이블에서 공통으로 재사용되는가
- 공통 예외 처리와 로깅이 필요한가
- 특정 테이블의 컬럼 구조에 강하게 의존하는가
- 다른 테이블이 들어오면 거의 그대로 재사용 가능한가

정리 기준은 아래처럼 둔다.

- 앞의 3개 질문에 더 많이 해당하면 클래스 메서드 후보
- 뒤의 2개 질문에 더 많이 해당하면 도메인 함수 후보

## 8. 예시 코드 블럭

아래 예시는 실제 적용 전 검토용이다. 그대로 복사해서 바로 확정하는 용도가 아니라, 구조를 어떻게 나눌지 보기 위한 기준 예시다.

### 8-1. 공통 연결 클래스를 두는 예시

```python
from neo4j import GraphDatabase
from graphdatascience import GraphDataScience


class Neo4jClient:
    def __init__(self, uri: str, user: str, password: str):
        self.uri = uri
        self.user = user
        self.password = password
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        self.gds = GraphDataScience(uri, auth=(user, password))

    def run_query(self, query: str, parameters: dict | None = None) -> list:
        with self.driver.session() as session:
            result = session.run(query, parameters or {})
            return [record for record in result]

    def execute_write(self, func, *args, **kwargs):
        with self.driver.session() as session:
            return session.execute_write(func, *args, **kwargs)

    def close(self):
        self.driver.close()
```

### 8-2. 도메인별 함수를 객체와 함께 사용하는 예시

```python
def import_equipment(tx, row):
    query = """
    MERGE (e:Equipment {id: $id})
    SET e.name = $name
    MERGE (t:ItemType {name: $type})
    MERGE (e)-[:HAS_TYPE]->(t)
    """
    tx.run(
        query,
        {
            "id": str(row["RowName"]),
            "name": row["Name"],
            "type": row["Type"],
        },
    )


def load_equipment_rows(client, df):
    for _, row in df.iterrows():
        client.execute_write(import_equipment, row)
```

### 8-3. 조회 템플릿을 분리하는 예시

```python
class EquipmentQueryTemplates:
    @staticmethod
    def by_grade(limit_no: int) -> str:
        return f"""
        MATCH (e:Equipment)-[:HAS_GRADE]->(g:Grade)
        RETURN e, g
        LIMIT {limit_no}
        """


def fetch_equipment_by_grade(client, limit_no: int):
    query = EquipmentQueryTemplates.by_grade(limit_no=limit_no)
    return client.run_query(query)
```

## 9. 우선 리팩터링 순서

### 1단계. 연결 구조 정리

- `Neo4j/connenct_neo4j.py`의 드라이버/GDS 생성 책임을 클래스 형태로 옮긴다.
- 이 단계에서는 기존 함수 인터페이스를 완전히 제거하지 말고, 필요하면 클래스 생성 래퍼만 제공한다.

### 2단계. 공통 실행 경로 정리

- `Neo4j/qurry_neo4j.py`의 `run_query()`를 클래스 메서드 또는 클래스 기반 래퍼로 이동한다.
- 세션 생성 방식과 공통 예외 처리 위치를 이 단계에서 고정한다.

### 3단계. 도메인 로직 분리 기준 적용

- `import_equipment()` 같은 로직은 도메인 함수로 유지하되, `client`를 받아 실행하는 구조로 정리한다.
- 다른 테이블이 추가될 때도 같은 방식으로 확장 가능한지 확인한다.

### 4단계. 템플릿화 후보 선정

- 조회 계열 중 반복 포맷이 명확한 쿼리만 템플릿 후보로 올린다.
- 적재 계열은 충분히 반복 패턴이 보이기 전까지 템플릿 공통화를 보류한다.

### 5단계. 문서 보강

- 구현이 확정된 부분은 이 문서의 예시 코드를 실제 코드 기준으로 교체한다.
- 보류 항목은 결론과 이유를 남기고, 더 이상 열려 있지 않다면 체크리스트에서 제거한다.

## 10. 보강이 필요한 현재 코드 메모

- `Neo4j` 폴더 안의 import 경로가 파일마다 일관되지 않다.
  - 예: 패키지 경로 사용과 상대 실행 가정이 섞여 있다.
- 파일명 오타가 포함되어 있다.
  - `connenct_neo4j.py`
  - `qurry_neo4j.py`
- 현재 적재는 행 단위 `iterrows()`와 반복 `execute_write()` 구조라서, 데이터 규모가 커지면 배치 처리 방식 검토가 필요하다.
- `clear_database_neo4j.py`는 전체 삭제 스크립트이므로, 여러 도메인이 공존할 경우 사용 범위를 더 명확히 해야 한다.

## 11. 현재 기준 결론

- 외부 참고 구현의 핵심 장점은 연결과 실행 책임이 한 객체에 모여 있다는 점이다.
- 현재 프로젝트는 여러 테이블과 다른 적재 규칙을 가질 가능성이 높으므로, 모든 도메인 로직을 클래스 메서드로 몰아넣는 방식은 당장 적합하지 않다.
- 따라서 현재 기준의 권장 방향은 다음과 같다.
  - 연결 객체는 클래스 기반으로 정리한다.
  - 공통 실행은 클래스 메서드로 모은다.
  - 도메인별 쿼리와 적재 로직은 별도 함수 또는 모듈로 유지한다.
  - 조회 템플릿은 선택적으로 도입하고, 적재 템플릿 공통화는 보류한다.
