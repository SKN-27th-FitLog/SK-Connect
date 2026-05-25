from __future__ import annotations

from kag_graph.extraction.models import EventSignal


ACTION_SIGNAL_MAPPING = {
    "RELEASE": ("출시", "배포", "릴리즈"),
    "ANNOUNCEMENT": ("공개", "발표"),
    "BUSINESS_DEAL": ("인수", "합병", "제휴"),
    "INVESTMENT": ("투자",),
    "SECURITY_RISK": ("해킹", "유출", "취약점"),
}


class ActionSignalExtractor:
    def extract(self, text: str) -> list[EventSignal]:
        signals: list[EventSignal] = []
        for action_type, aliases in ACTION_SIGNAL_MAPPING.items():
            for alias in aliases:
                if alias in text:
                    signals.append(
                        EventSignal(
                            action_type=action_type,
                            matched_text=alias,
                            confidence=0.8,
                            source="morph_action_dictionary",
                        )
                    )
        return signals
