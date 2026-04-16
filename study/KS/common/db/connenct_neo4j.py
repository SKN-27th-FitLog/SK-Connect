# Neo4j Python 드라이버를 import합니다.
# GraphDatabase: Neo4j 데이터베이스와 통신하기 위한 드라이버 클래스
from neo4j import GraphDatabase


# ============================================
# Cypher 쿼리 실행 헬퍼 함수
# ============================================
def run_query(query, parameters=None):
    """
    Cypher 쿼리를 실행하는 헬퍼 함수
    
    Args:
        query (str): 실행할 Cypher 쿼리 문자열
        parameters (dict, optional): 쿼리에 전달할 파라미터 딕셔너리
    
    Returns:
        list: 쿼리 결과 레코드들의 리스트
    
    사용 예시:
        result = run_query("MATCH (p:Person) RETURN p.name")
    """
    # driver.session(): 데이터베이스 세션 생성
    # 세션은 쿼리를 실행하는 컨텍스트를 제공합니다.
    with driver.session() as session:
        # session.run(): Cypher 쿼리를 실행
        # parameters or {}: 파라미터가 없으면 빈 딕셔너리 사용
        result = session.run(query, parameters or {})
        
        # 결과를 리스트로 변환하여 반환
        # record: 쿼리 결과의 각 행을 나타내는 객체
        return [record for record in result]




if __name__ == "__main__":
    # ============================================
    # Neo4j 연결 정보 설정
    # ============================================
    # URI: Neo4j 데이터베이스의 주소
    #   - bolt:// : Neo4j의 네이티브 프로토콜 (포트 7687)
    #   - localhost:7687 : 로컬 컴퓨터의 Neo4j 서버
    URI = "bolt://localhost:7687"

    # USERNAME: Neo4j 데이터베이스 사용자명 (기본값: neo4j)
    USERNAME = "neo4j"

    # PASSWORD: Neo4j 데이터베이스 비밀번호
    # 주의: 실제 환경에서는 환경변수나 설정 파일에서 읽어오는 것이 안전합니다.
    PASSWORD = "test1234"  # 실제 비밀번호로 변경하세요.

    # ============================================
    # Neo4j 드라이버 생성
    # ============================================
    # driver: Neo4j 데이터베이스와의 연결을 관리하는 드라이버 객체
    # GraphDatabase.driver(): URI와 인증 정보를 사용하여 드라이버 생성
    driver = GraphDatabase.driver(URI, auth=(USERNAME, PASSWORD))



    # ============================================
    # 연결 테스트
    # ============================================
    # Neo4j 연결이 정상적으로 작동하는지 확인합니다.
    try:
        # 간단한 테스트 쿼리 실행
        # "RETURN 1 as test": 숫자 1을 반환하는 간단한 쿼리
        result = run_query("RETURN 1 as test")
        print("Neo4j 연결 성공!")
    except Exception as e:
        # 연결 실패 시 에러 메시지 출력
        print(f"Neo4j 연결 실패: {e}")