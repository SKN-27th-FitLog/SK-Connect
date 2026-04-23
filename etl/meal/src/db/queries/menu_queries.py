"""
메뉴 관련 SQL 상수를 정의합니다.
"""

INSERT_MENU = """
INSERT INTO menu (shop_id, name, price)
VALUES (%s, %s, %s)
RETURNING menu_id
"""
