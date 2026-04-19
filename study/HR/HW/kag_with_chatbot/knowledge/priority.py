"""
knowledge/priority.py — 제약 강도 우선순위 관리

사용자 발화에서 추출된 제약 조건의 강도(Strength)를
숫자 우선순위로 변환하여 충돌 시 해결에 사용합니다.

[강도 체계] (숫자가 낮을수록 우선순위 높음)
    1. HARD_NEGATIVE : 절대 제외 (~말고, ~빼고)
    2. ABSOLUTE      : 양보 불가능한 필수 조건
    3. STRONG        : 강조되었으나 승인 하에 완화 가능
    4. INFERRED      : 문맥에서 추론된 암묵적 선호
    5. PREFERENCE    : 일반적인 선호 (가성비, 분위기 등)

[사용처]
    - core/nodes/parser.py    : 키워드 강도 할당 후 정렬
    - core/nodes/validator.py : ABSOLUTE 위반 검증
"""


class PriorityResolver:
    """
    제약 강도 문자열을 숫자 우선순위로 변환하는 리졸버.

    사용 예:
        priority = PriorityResolver.get_priority("ABSOLUTE")  # → 2
        priority = PriorityResolver.get_priority("PREFERENCE") # → 5
    """

    # 강도 → 우선순위 매핑 (낮을수록 높은 우선순위)
    PRIORITY_MAP = {
        "HARD_NEGATIVE": 1,
        "ABSOLUTE": 2,
        "STRONG": 3,
        "INFERRED": 4,
        "PREFERENCE": 5,
    }

    @classmethod
    def get_priority(cls, strength: str) -> int:
        """
        강도 문자열을 숫자 우선순위로 변환합니다.

        Args:
            strength: 강도 문자열 (예: "ABSOLUTE", "STRONG")

        Returns:
            우선순위 숫자 (1~5). 알 수 없는 강도는 99 반환.
        """
        return cls.PRIORITY_MAP.get(strength.upper(), 99)
