from kag_graph.interpreter import PathInterpreter


def test_interpreter_uses_only_evidence_paths():
    interpreter = PathInterpreter()
    answer = interpreter.explain(
        user_query="면은 싫은데 중국집 가고 싶어",
        evidence_paths=["Restaurant(홍콩반점)-[:SELLS]->Menu(중국음식)"],
    )

    assert "홍콩반점" in answer
    assert "근거" in answer
