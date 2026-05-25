from kag_graph.llm_assist import LLMAssistResult


def test_llm_assist_result_is_candidate_only():
    result = LLMAssistResult(
        candidates=[{"node_label": "Menu", "raw_value": "중국집", "candidate_value": "중국음식", "confidence": 0.81}],
        confidence=0.81,
        reason="candidate suggestion",
        needs_clarification=False,
    )

    assert result.candidates[0]["candidate_value"] == "중국음식"
    assert not hasattr(result, "cypher")
