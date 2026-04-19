"""
knowledge/policy.py — 운영 정책 선택기

현재 UI 모드(SEARCH, RELAXATION_PROPOSAL 등)와
완화 깊이(relaxation_depth)를 기반으로
시스템의 운영 모드(STRICT vs LENIENT)를 결정합니다.

[모드 정의]
    STRICT  : 최초 검색. 지리적 확장 금지, 카테고리 일치 필수.
    LENIENT : 완화 단계. 반경 확장, 인접 카테고리 확장 허용.

[사용처]
    - knowledge/rules.py : 노드별 규칙 조회 시 모드를 결정
"""


class PolicySelector:
    """
    시스템의 운영 모드를 결정하는 정책 선택기.

    완화가 진행 중이거나 사용자가 완화를 요청한 경우
    LENIENT 모드로 전환하여 검색 범위를 넓힙니다.
    """

    @staticmethod
    def get_operational_mode(ui_mode: str, relaxation_depth: int) -> str:
        """
        현재 상태를 기반으로 운영 모드를 결정합니다.

        Args:
            ui_mode          : 현재 UI 동작 모드 (SEARCH, RELAXATION_PROPOSAL 등)
            relaxation_depth : 지금까지 완화가 적용된 횟수

        Returns:
            "STRICT" (엄격 모드) 또는 "LENIENT" (완화 모드)

        규칙:
            - RELAXATION_PROPOSAL 상태이거나 이미 완화가 1회 이상 진행되면 LENIENT
            - 그 외에는 STRICT (최초 검색)
        """
        if ui_mode == "RELAXATION_PROPOSAL" or relaxation_depth > 0:
            return "LENIENT"
        return "STRICT"
