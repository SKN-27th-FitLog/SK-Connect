"""
app.py — Streamlit 기반 맛집 추천 챗봇 UI

사용자와 대화형 인터페이스를 제공하는 진입점입니다.

[기능]
    1. 채팅 인터페이스 (Streamlit chat_message)
    2. 추천 결과 시각화 (expander + columns)
    3. 좋아요/싫어요 버튼을 통한 피드백 수집
    4. 세션 관리 (UUID 기반, 초기화 가능)

[아키텍처]
    app.py → core.graph.app_graph.invoke() → LangGraph 파이프라인

[실행 방법]
    streamlit run app.py
"""

import streamlit as st
import uuid

from core.graph import app_graph
from utils.logger import get_logger

logger = get_logger("App")

# ── 페이지 설정 ──────────────────────────────
st.set_page_config(
    page_title="개인화 맛집 챗봇",
    page_icon="🍴",
    layout="centered",
)

# ══════════════════════════════════════════════
# 1. 세션 상태 초기화
# ══════════════════════════════════════════════
# Streamlit은 매 상호작용마다 스크립트를 재실행하므로
# st.session_state에 영속 데이터를 저장합니다.

if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

if "messages" not in st.session_state:
    st.session_state.messages = []

if "viewed_ids" not in st.session_state:
    st.session_state.viewed_ids = []

# ══════════════════════════════════════════════
# 2. UI 헤더
# ══════════════════════════════════════════════
st.title("🍴 나만을 위한 맛집 비서")
st.markdown("Neo4j와 LangGraph를 활용한 개인화 맛집 추천 서비스입니다.")

# ══════════════════════════════════════════════
# 3. 기존 채팅 기록 출력
# ══════════════════════════════════════════════
# 세션에 저장된 모든 메시지를 순서대로 렌더링합니다.
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# ══════════════════════════════════════════════
# 4. 사용자 입력 및 에이전트 호출
# ══════════════════════════════════════════════
if prompt := st.chat_input("어디서 어떤 음식을 드시고 싶으신가요?"):
    # ── 사용자 메시지 표시 및 저장 ──────
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # ── LangGraph 에이전트 실행 ──────
    with st.chat_message("assistant"):
        with st.spinner("맛집을 찾고 있습니다..."):
            # 초기 상태 구성: AgentState의 모든 필수 필드를 설정
            initial_state = {
                "session_id": st.session_state.session_id,
                "user_input": prompt,
                "hard_constraints": {},
                "soft_preferences": {},
                "inferred_preferences": {},
                "ambiguous_goals": {},
                "relaxation_history": [],
                "validation_report": [],
                "area": None,
                "category": None,
                "restaurant_name": None,
                "excluded_names": [],
                "excluded_categories": [],
                "limit": 5,
                "recommendations": [],
                "explanation": "",
                "current_level": 1,
                "viewed_ids": st.session_state.viewed_ids,
                "feedback_type": None,
                "feedback_content": None,
                "target_id": None,
            }

            # 그래프 실행 (SQLite 체크포인터용 thread config 전달)
            config = {
                "configurable": {"thread_id": st.session_state.session_id}
            }
            result = app_graph.invoke(initial_state, config=config)

            # viewed_ids 동기화 (다음 턴에서 중복 방지에 활용)
            st.session_state.viewed_ids = result.get("viewed_ids", [])

            response = result["explanation"]
            st.markdown(response)

            # ── 추천 상세 정보 시각화 ──────
            if result.get("recommendations"):
                with st.expander("추천 상세 정보", expanded=True):
                    for i, rec in enumerate(result["recommendations"]):
                        col1, col2, col3 = st.columns([4, 1, 1])

                        # 식당명과 평점 표시
                        with col1:
                            st.write(
                                f"**{i+1}. {rec['name']}** "
                                f"(평점: {rec.get('rating', 'N/A')})"
                            )

                        # 좋아요 버튼
                        if col2.button(
                            "👍",
                            key=f"like_{i}_{rec.get('id', rec['name'])}",
                        ):
                            app_graph.invoke(
                                {
                                    **initial_state,
                                    "feedback_type": "LIKE",
                                    "target_id": rec.get("id", rec["name"]),
                                    "feedback_content": "좋아요 버튼 클릭",
                                },
                                config=config,
                            )
                            st.success(f"'{rec['name']}' 선호도가 반영되었습니다!")

                        # 싫어요 버튼
                        if col3.button(
                            "👎",
                            key=f"dislike_{i}_{rec.get('id', rec['name'])}",
                        ):
                            app_graph.invoke(
                                {
                                    **initial_state,
                                    "feedback_type": "DISLIKE",
                                    "target_id": rec.get("id", rec["name"]),
                                    "feedback_content": "싫어요 버튼 클릭",
                                },
                                config=config,
                            )
                            st.error(f"'{rec['name']}'는 검색에서 제외됩니다.")

    # 어시스턴트 응답 저장
    st.session_state.messages.append({"role": "assistant", "content": response})

# ══════════════════════════════════════════════
# 5. 사이드바 (세션 관리)
# ══════════════════════════════════════════════
with st.sidebar:
    st.header("설정")
    st.write(f"Session ID: `{st.session_state.session_id}`")

    if st.button("대화 초기화"):
        st.session_state.messages = []
        st.session_state.session_id = str(uuid.uuid4())
        st.rerun()
