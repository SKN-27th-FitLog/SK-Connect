"""
코드 테이블 조회를 위한 SQL 상수를 정의합니다.
v4 설계 원칙에 따라 SQL 쿼리는 상수화하여 관리합니다.
"""

# 코드 테이블 전체 조회
SELECT_ALL_CODES = 'SELECT cd, name, cd_info, cd_upper FROM "codeT"'

# 특정 프리픽스로 코드 조회
SELECT_CODES_BY_PREFIX = 'SELECT cd, name, cd_info FROM "codeT" WHERE cd LIKE %s'

# 카테고리 코드 존재 여부 확인
EXISTS_CATEGORY_CODE = "SELECT 1 FROM \"codeT\" WHERE cd = %s AND cd LIKE 'CA%%' LIMIT 1"

