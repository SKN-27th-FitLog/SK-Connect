"""
knowledge 패키지 — 도메인 지식 및 규칙 관리

음식 도메인의 온톨로지, 제약 우선순위, 운영 정책,
그리고 LLM 행동 규격(RULE.MD)을 통합적으로 관리합니다.

[포함 모듈]
    - ontology.py : 키워드-카테고리 매핑, 유의어, 지명 패턴
    - priority.py : 제약 강도 우선순위 (HARD_NEGATIVE > ABSOLUTE > ...)
    - policy.py   : 운영 모드 선택기 (STRICT vs LENIENT)
    - rules.py    : RULE.MD 파서 및 통합 RuleEngine

[사용법]
    from knowledge import rule_engine
    rules_text = rule_engine.get_node_rules("parser")
    category = rule_engine.ontology.map_keyword("파스타")  # → "양식"
"""

from knowledge.rules import RuleEngine

# 싱글톤 인스턴스: 프로젝트 전역에서 이 객체를 import하여 사용
rule_engine = RuleEngine()

__all__ = ["rule_engine", "RuleEngine"]
