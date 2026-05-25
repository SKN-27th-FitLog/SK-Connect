class PathInterpreter:
    def explain(self, user_query: str, evidence_paths: list[str]) -> str:
        if not evidence_paths:
            return "근거 path가 없어 답변을 생성하지 않습니다. 추가 조건을 확인해야 합니다."

        evidence = "\n".join(f"- {path}" for path in evidence_paths)
        return f"요청: {user_query}\n근거:\n{evidence}"
