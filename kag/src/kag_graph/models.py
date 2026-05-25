from dataclasses import dataclass


@dataclass(frozen=True)
class ClassificationResult:
    value: str
    confidence: float
    reason: str
    needs_llm_assist: bool = False


@dataclass(frozen=True)
class ExtractedSlot:
    slot_type: str
    node_label: str
    raw_value: str
    normalized_value: str
    confidence: float
    is_negative: bool
    is_required: bool

    @property
    def query_value(self) -> str:
        return self.normalized_value


@dataclass(frozen=True)
class QueryBuildResult:
    template_name: str
    query_text: str
    params: dict[str, object]
    expected_path_pattern: str


@dataclass(frozen=True)
class GraphNodeDTO:
    labels: list[str]
    properties: dict[str, object]


@dataclass(frozen=True)
class GraphRelationshipDTO:
    type: str
    start_node: GraphNodeDTO
    end_node: GraphNodeDTO
    properties: dict[str, object]


@dataclass(frozen=True)
class EvidencePathDTO:
    nodes: list[GraphNodeDTO]
    relationships: list[GraphRelationshipDTO]


@dataclass(frozen=True)
class GraphSearchResultDTO:
    result_node: GraphNodeDTO
    evidence_paths: list[EvidencePathDTO]
    score: float


@dataclass(frozen=True)
class ValidationResult:
    is_valid: bool
    slots: list[ExtractedSlot]
    status: str
    message: str | None = None
