"""
database/neo4j_client.py — Neo4j 그래프 DB 클라이언트 (싱글톤)

Neo4j 데이터베이스 연결, 쿼리 실행, 쓰기 작업을
관리하는 클라이언트 클래스를 제공합니다.

[싱글톤 패턴]
    클래스 전체를 통해 하나의 인스턴스만 생성됩니다.
    __new__에서 기존 인스턴스를 반환하여 커넥션을 재사용합니다.

[사용법]
    from database.neo4j_client import neo4j_client
    results = neo4j_client.run_query("MATCH (n) RETURN n LIMIT 10")
    neo4j_client.execute_write("CREATE (n:Test {name: 'test'})")

[설계 원칙]
    - 환경 변수는 config.settings에서만 읽습니다.
    - 연결 실패 시에도 앱이 크래시하지 않습니다 (driver=None).
    - 모든 쿼리와 파라미터는 로그에 기록됩니다 (감사 추적).
"""

from neo4j import GraphDatabase
from utils.logger import get_logger
from config.settings import settings

logger = get_logger("Neo4jClient")


class Neo4jClient:
    """
    Neo4j 드라이버를 감싸는 싱글톤 클라이언트.

    Attributes:
        uri      : Neo4j Bolt 프로토콜 URI
        user     : 인증 사용자명
        password : 인증 비밀번호
        driver   : Neo4j 드라이버 객체 (연결 실패 시 None)
    """
    _instance = None

    def __new__(cls):
        """
        싱글톤 패턴 구현: 최초 호출 시에만 인스턴스를 생성합니다.
        이후 호출에서는 동일 인스턴스를 반환합니다.
        """
        if cls._instance is None:
            cls._instance = super(Neo4jClient, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """
        Neo4j 드라이버를 초기화합니다.
        이미 초기화된 경우 중복 실행을 방지합니다.

        연결 흐름:
            1. config.settings에서 URI, 사용자명, 비밀번호 읽기
            2. GraphDatabase.driver()로 드라이버 생성
            3. verify_connectivity()로 연결 상태 검증
            4. 실패 시 driver=None (쿼리 메서드에서 빈 결과 반환)
        """
        if self._initialized:
            return

        self.uri = settings.NEO4J_URI
        self.user = settings.NEO4J_USER
        self.password = settings.NEO4J_PASSWORD

        try:
            self.driver = GraphDatabase.driver(
                self.uri, auth=(self.user, self.password)
            )
            self.driver.verify_connectivity()
            logger.info("Successfully connected to Neo4j")
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            self.driver = None

        self._initialized = True

    def close(self):
        """
        Neo4j 드라이버 연결을 안전하게 종료합니다.
        앱 종료 시 또는 재연결 전에 호출합니다.
        """
        if self.driver:
            self.driver.close()

    def run_query(self, cypher_query: str, parameters: dict = None) -> list:
        """
        읽기 전용 Cypher 쿼리를 실행하고 결과를 딕셔너리 리스트로 반환합니다.

        Args:
            cypher_query: 실행할 Cypher 쿼리 문자열
            parameters  : 쿼리 파라미터 딕셔너리 (선택)

        Returns:
            쿼리 결과 리스트. 각 항목은 {컬럼명: 값} 딕셔너리.
            드라이버가 없으면(연결 실패) 빈 리스트 반환.

        로그:
            - 쿼리 앞 100자와 파라미터를 INFO 레벨로 기록합니다.
        """
        if not self.driver:
            return []

        logger.info(f"Query: {cypher_query.strip()[:100]}...")
        if parameters:
            logger.info(f"Params: {parameters}")

        with self.driver.session() as session:
            result = session.run(cypher_query, parameters)
            return [record.data() for record in result]

    def execute_write(self, cypher_query: str, parameters: dict = None):
        """
        쓰기 전용 Cypher 쿼리를 실행합니다 (MERGE, CREATE, SET 등).

        Args:
            cypher_query: 실행할 Cypher 쿼리 문자열
            parameters  : 쿼리 파라미터 딕셔너리 (선택)

        Returns:
            None. 결과를 반환하지 않습니다.

        로그:
            - 쿼리 앞 100자와 파라미터를 INFO 레벨로 기록합니다.
        """
        if not self.driver:
            return

        logger.info(f"Write Query: {cypher_query.strip()[:100]}...")
        if parameters:
            logger.info(f"Params: {parameters}")

        with self.driver.session() as session:
            session.run(cypher_query, parameters)


# ──────────────────────────────────────────────
# 싱글톤 인스턴스 (프로젝트 전역에서 import하여 사용)
# ──────────────────────────────────────────────
neo4j_client = Neo4jClient()
