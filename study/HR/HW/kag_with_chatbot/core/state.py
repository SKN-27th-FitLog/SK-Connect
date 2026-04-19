"""
core/state.py — LangGraph 공용 상태 스키마 (AgentState)

모든 그래프 노드가 공유하는 상태 딕셔너리의 타입을 정의합니다.
LangGraph의 StateGraph는 이 스키마를 기반으로
노드 간 데이터를 전달하고 체크포인팅합니다.

[설계 원칙]
- 단일 진실 원천(Single Source of Truth):
  모든 노드가 동일한 AgentState를 읽고 쓰므로
  필드 이름과 타입의 일관성이 매우 중요합니다.
- Annotated 타입을 사용해 LangGraph의 상태 병합 전략을 지정합니다.
  예: chat_history는 operator.add로 리스트를 누적 병합합니다.
"""

from typing import TypedDict, List, Optional, Annotated, Dict, Any
import operator


# ──────────────────────────────────────────────
# 보조 타입 정의 (Sub-schemas)
# ──────────────────────────────────────────────

class MetaIntent(TypedDict):
    """
    사용자 의도에 대한 메타 정보를 담는 구조체.

    Fields:
        count          : 사용자가 원하는 추천 결과 수 (기본 5)
        diversity_flag : 다양성 요청 여부 (예: "여러 종류로 보여줘")
        diversity_type : 다양성 유형 (CATEGORY, TASTE, ATMOSPHERE 중 하나)
        ambiguity_score: 의도 모호도 점수 (0.0 = 명확, 1.0 = 매우 모호)
        intent_type    : 의도 유형 (recommend, search, compare, history_recall)
        recall_anchor  : 히스토리 회상 기준 (first, last, recent, unspecified)
        recall_scope   : 히스토리 회상 범위 (global_session, recent_window, specific_turn)
    """
    count: int
    diversity_flag: bool
    diversity_type: Optional[str]
    ambiguity_score: float
    intent_type: str
    recall_anchor: Optional[str]
    recall_scope: Optional[str]


class ClarificationOption(TypedDict):
    """
    재질의(Clarification) 시 사용자에게 제시할 선택지.

    Fields:
        id          : 선택지 식별자 (예: "A", "B", "C")
        label       : 짧은 라벨 텍스트
        description : 선택지에 대한 안내 설명
    """
    id: str
    label: str
    description: str


# ──────────────────────────────────────────────
# 메인 상태 스키마
# ──────────────────────────────────────────────

class AgentState(TypedDict):
    """
    LangGraph StateGraph의 전체 상태를 정의하는 TypedDict.

    각 노드(Parser, Recommender, Validator, Generator, Clarifier, Feedback)는
    이 상태를 읽고 부분적으로 업데이트합니다.

    섹션별로 필드를 구분합니다:
      - 세션/입력 필드
      - 핵심 검색 필드 (필터, 선호, 시그널)
      - 행동 가드레일 필드
      - 시맨틱 매핑 필드
      - 재질의(Clarification) 필드
      - 컨텍스트 회상 필드
      - 추천 결과 필드
      - 피드백 필드
    """

    # ─── 세션/입력 ────────────────────────────
    session_id: str                                     # 사용자 세션 고유 ID (UUID)
    user_input: str                                     # 현재 턴의 사용자 발화 원문
    chat_history: Annotated[List[dict], operator.add]   # 대화 이력 (누적 병합)

    # ─── 핵심 검색 필드 ───────────────────────
    area: Optional[str]                 # 지역/행정구역 (예: "강남구", "홍대")
    category: Optional[str]             # 음식 대분류 카테고리 (예: "한식", "양식")
    restaurant_name: Optional[str]      # 특정 식당명 검색 시 사용

    hard_filters: dict                  # 결과 집합을 직접 제한하는 필수 조건
    soft_preferences: dict              # 점수에 반영되는 정성적 선호 조건 (분위기 등)
    ranking_signals: list               # 점수 조정자 슬롯 (맛집, 유명한 등)
    inferred_preferences: dict          # 대화 문맥에서 추론된 암묵적 선호
    ambiguous_goals: dict               # 모호한 정보 (Ranking Hint 용도)

    # ─── 시맨틱 매핑 필드 ─────────────────────
    positive_keywords: List[str]                # 긍정 키워드 목록 (메뉴, 특징 등)
    keyword_strengths: Dict[str, str]           # 키워드별 강도 (value → ABSOLUTE/STRONG/PREFERENCE)
    keyword_intent: List[dict]                  # 키워드 인텐트 상세 (value, strength, mapped_category)
    inferred_categories: List[str]              # 광의 의도에서 추론된 후보 카테고리 목록

    excluded_categories: List[str]              # 제외할 카테고리 (HARD_NEGATIVE)
    excluded_names: List[str]                   # 제외할 식당명 (HARD_NEGATIVE)
    negative_keywords: List[str]                # 제외할 키워드 (HARD_NEGATIVE)
    constraint_strength: dict                   # 필드별 제약 강도 (레거시 호환)

    # ─── 행동 가드레일 필드 ───────────────────
    search_mode: str                    # 검색 모드 (DISCOVERY, SEMI_DISCOVERY, FILTERED_SEARCH)
    relaxation_depth: int               # 완화 적용 횟수 (MAX_DEPTH 제어용)
    relaxation_history: List[dict]      # 과거 완화 이력 (호환성 유지)
    relaxation_plan: dict               # 완화 계획 (trigger_reason, candidate_actions, approved_action)
    rejection_log: List[dict]           # 검증 탈락 로그 (id, name, rule_id, failure_reason)

    ui_mode: str                        # UI 동작 모드 (SEARCH, CLARIFICATION, RELAXATION_PROPOSAL 등)
    explanation_payload: dict           # 전략적 변화 근거 기록 (Fallback, Discovery 등)

    # ─── 재질의(Clarification) 필드 ──────────
    meta_intent: MetaIntent                         # 사용자 의도 메타 정보
    clarification_needed: bool                      # 재질의 필요 여부 플래그
    clarification_options: List[ClarificationOption] # 재질의 선택지 목록
    clarification_answer: Optional[str]             # 사용자가 선택한 재질의 답변

    # ─── 컨텍스트 회상 필드 ───────────────────
    recommendation_records: List[dict]  # 추천 이력 (turn_index, category, ids, intent_snapshot)
    resolved_target_id: Optional[str]   # 회상 대상으로 확정된 식당 ID

    # ─── 추천 결과 필드 ──────────────────────
    limit: int                          # 최대 추천 개수 (기본 5)
    recommendations: List[dict]         # 최종 추천 결과 리스트
    validation_report: List[dict]       # 개별 아이템 검증 리포트
    explanation: str                    # 최종 사용자 응답 텍스트 (UI 표시용)

    # ─── 피드백 필드 ─────────────────────────
    viewed_ids: List[str]               # 이미 본 식당 ID 목록 (중복 방지)
    current_level: int                  # 현재 워터폴 레벨
    feedback_type: Optional[str]        # 피드백 분류 결과 (LIKE, DISLIKE, RETRY 등)
    feedback_content: Optional[str]     # 피드백 원문 텍스트
    target_id: Optional[str]            # 피드백/인터랙션 대상 식당 ID
