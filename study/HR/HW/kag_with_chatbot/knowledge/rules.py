"""
knowledge/rules.py — RULE.MD 행동 규격서 파서 및 룰 엔진

RULE.MD 파일을 섹션별로 파싱하여
각 LLM 노드에 필요한 행동 규칙을 제공합니다.

[동작 흐름]
    1. RuleLoader가 RULE.MD 파일을 읽어 섹션별로 분할
    2. RuleEngine이 노드 이름과 운영 모드에 따라
       적절한 규칙 텍스트를 조합하여 반환
    3. 조합된 규칙 텍스트는 LLM 프롬프트에 삽입됨

[사용처]
    - core/nodes/parser.py    : 파서 노드 행동 규격
    - core/nodes/generator.py : 응답 생성기 행동 규격
"""

import os
import re
from typing import Dict

from utils.logger import get_logger
from knowledge.ontology import OntologyLayer
from knowledge.priority import PriorityResolver
from knowledge.policy import PolicySelector

logger = get_logger("RuleEngine")


class RuleLoader:
    """
    RULE.MD 파일을 파싱하여 섹션별 규칙 텍스트를 추출하는 로더.

    RULE.MD는 마크다운 형식으로 작성되며,
    ## 헤더를 기준으로 GLOBAL, PARSER, GENERATOR 등의
    섹션으로 분할됩니다.

    Attributes:
        file_path : RULE.MD 파일 경로
        _rules    : 파싱된 섹션 딕셔너리 {섹션명: 규칙 텍스트}
    """

    def __init__(self, file_path: str = "RULE.MD"):
        """
        RuleLoader를 초기화하고 규칙 파일을 즉시 로드합니다.

        Args:
            file_path: RULE.MD 파일 경로 (기본: 프로젝트 루트의 RULE.MD)
        """
        self.file_path = file_path
        self._rules: Dict[str, str] = {}
        self.load_rules()

    def load_rules(self):
        """
        RULE.MD 파일을 읽고 ## 헤더 기준으로 섹션을 분할합니다.

        파싱 로직:
            - `## 1. [GLOBAL] ...` 형식의 헤더를 찾습니다.
            - 대괄호 안의 키워드(GLOBAL, PARSER 등)를 섹션 키로 사용합니다.
            - 다음 ## 헤더까지의 내용을 해당 섹션의 규칙으로 저장합니다.
            - 파일이 없으면 기본 글로벌 규칙만 설정합니다.
        """
        if not os.path.exists(self.file_path):
            logger.error(f"Rule file not found at {self.file_path}")
            self._rules = {"GLOBAL": "Default: Follow common sense."}
            return

        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # 유연한 정규식: ## 숫자. [키워드] 형식의 헤더를 파싱
            for full_title, section_key, section_content in re.findall(
                r"##\s*(\d+\.\s*\[?(\w+)\]?.*?)\n(.*?)(?=\n##|$)",
                content,
                re.DOTALL,
            ):
                self._rules[section_key.upper()] = section_content.strip()

            logger.info(f"Loaded rules: {list(self._rules.keys())}")
        except Exception as e:
            logger.error(f"Failed to load rules: {e}")

    def get_section(self, section_name: str) -> str:
        """
        섹션 이름으로 해당 규칙 텍스트를 조회합니다.

        Args:
            section_name: 섹션 키 (예: "GLOBAL", "PARSER", "GENERATOR")

        Returns:
            해당 섹션의 규칙 텍스트. 존재하지 않으면 빈 문자열.
        """
        return self._rules.get(section_name.upper(), "")


class RuleEngine:
    """
    온톨로지, 우선순위, 정책, 규칙 로더를 통합하는 중앙 룰 엔진.

    각 그래프 노드는 이 엔진을 통해:
      1. 온톨로지에서 키워드를 매핑하고
      2. 현재 운영 모드에 맞는 행동 규칙을 조회하고
      3. 제약 강도의 우선순위를 해석합니다.

    Attributes:
        loader   : RULE.MD 파서 (RuleLoader)
        priority : 제약 강도 리졸버 (PriorityResolver)
        policy   : 운영 모드 선택기 (PolicySelector)
        ontology : 음식 도메인 온톨로지 (OntologyLayer)
    """

    def __init__(self, file_path: str = "RULE.MD"):
        """
        RuleEngine을 초기화합니다.

        Args:
            file_path: RULE.MD 파일 경로
        """
        self.loader = RuleLoader(file_path)
        self.priority = PriorityResolver()
        self.policy = PolicySelector()
        self.ontology = OntologyLayer()

    def get_node_rules(
        self,
        node_name: str,
        ui_mode: str = "SEARCH",
        relaxation_depth: int = 0,
    ) -> str:
        """
        특정 노드에 맞는 행동 규칙 텍스트를 조합하여 반환합니다.

        반환되는 텍스트는 LLM 프롬프트에 직접 삽입됩니다.

        Args:
            node_name        : 노드 이름 (예: "parser", "generator")
            ui_mode          : 현재 UI 모드 (기본: "SEARCH")
            relaxation_depth : 완화 적용 횟수 (기본: 0)

        Returns:
            조합된 규칙 텍스트 (글로벌 + 노드별 + 전략 규칙)

        조합 순서:
            1. GLOBAL 규칙 (모든 노드 공통)
            2. 해당 노드 전용 규칙 (PARSER, GENERATOR 등)
            3. STRATEGY 규칙 (운영 정책)
        """
        mode = self.policy.get_operational_mode(ui_mode, relaxation_depth)
        global_rules = self.loader.get_section("GLOBAL")
        node_rules = self.loader.get_section(node_name.upper())
        strategy_rules = self.loader.get_section("STRATEGY")

        combined_rules = (
            f"### [BEHAVIORAL RULES - {mode} MODE]\n"
            f"{global_rules}\n\n"
            f"### [SPECIFIC RULES FOR {node_name.upper()}]\n"
            f"{node_rules}\n\n"
            f"### [OPERATIONAL STRATEGY]\n"
            f"{strategy_rules}"
        )
        return combined_rules
